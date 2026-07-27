# ============================================================
# modules/llm_analyzer.py
#
# Responsibility: Ollama/Llama3 inference layer.
# Accepts structured analysis context, calls the LLM,
# and returns a parsed LLMReport ready for the UI.
#
# Public API
# ----------
# analyze_resume(ctx: PromptContext) -> LLMReport
# parse_sections(raw_markdown: str)  -> dict[str, str]
# check_ollama_connection()          -> ConnectionStatus
#
# LLMReport (TypedDict)
#   success        bool
#   raw_markdown   str       — full LLM output (for debug)
#   sections       dict      — keyed by section title
#   error          str       — empty on success
#   model          str       — model name used
#   duration_s     float     — wall-clock inference time
#
# ConnectionStatus (TypedDict)
#   available      bool
#   model_ready    bool
#   error          str
# ============================================================

from __future__ import annotations

import logging
import re
import time
from typing import TypedDict

import ollama

from config.settings import OLLAMA_MODEL, OLLAMA_BASE_URL, OLLAMA_TIMEOUT
from modules.prompts import PromptContext, SYSTEM_PROMPT, build_analysis_prompt

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Section registry
# Keys must match the headings in prompts.py EXACTLY (case-insensitive match).
# The order here defines the display order in the UI.
# ─────────────────────────────────────────────────────────────────────────────

SECTION_KEYS: list[str] = [
    "Overall Resume Review",
    "Strengths",
    "Weaknesses",
    "Missing Technical Skills",
    "Suggestions for Improvement",
    "Resume Summary",
    "Career Advice",
    "Improved Bullet Points",
    "Interview Questions",
]

# ─────────────────────────────────────────────────────────────────────────────
# Return types
# ─────────────────────────────────────────────────────────────────────────────

class LLMReport(TypedDict):
    success:      bool
    raw_markdown: str
    sections:     dict[str, str]
    error:        str
    model:        str
    duration_s:   float


class ConnectionStatus(TypedDict):
    available:   bool
    model_ready: bool
    error:       str


# ─────────────────────────────────────────────────────────────────────────────
# Connection check
# ─────────────────────────────────────────────────────────────────────────────

def check_ollama_connection() -> ConnectionStatus:
    """
    Verify that the Ollama daemon is running and the target model is available.

    Returns a ConnectionStatus so the UI can show a helpful error instead of
    crashing when Ollama is not running.
    """
    try:
        models_response = ollama.list()
        # models_response.models is a list of Model objects with a .model attribute
        available_models: list[str] = [
            m.model for m in models_response.models
        ]
        # Strip tag suffixes for comparison (e.g. "llama3:latest" → "llama3")
        base_names = [m.split(":")[0] for m in available_models]
        model_ready = OLLAMA_MODEL in available_models or OLLAMA_MODEL in base_names

        logger.info(
            "Ollama connection OK. Available models: %s. Target '%s' ready: %s",
            available_models, OLLAMA_MODEL, model_ready,
        )
        return ConnectionStatus(
            available=True,
            model_ready=model_ready,
            error="" if model_ready else (
                f"Model '{OLLAMA_MODEL}' not found. "
                f"Run: ollama pull {OLLAMA_MODEL}"
            ),
        )
    except Exception as exc:
        logger.error("Ollama connection failed: %s", exc)
        return ConnectionStatus(
            available=False,
            model_ready=False,
            error=(
                f"Cannot connect to Ollama at {OLLAMA_BASE_URL}. "
                f"Make sure Ollama is running: ollama serve"
            ),
        )


# ─────────────────────────────────────────────────────────────────────────────
# Section parser
# ─────────────────────────────────────────────────────────────────────────────

def parse_sections(raw_markdown: str) -> dict[str, str]:
    """
    Split the LLM's raw markdown output into a dict keyed by section title.

    Handles:
    - ``## 1. Overall Resume Review`` style headings (numbered)
    - ``## Overall Resume Review``    style headings (un-numbered)

    Matching is case-insensitive and strips surrounding whitespace.
    Sections not found in the output get an empty string value so the
    UI always has all seven keys to work with.

    Parameters
    ----------
    raw_markdown : str
        The complete text returned by the LLM.

    Returns
    -------
    dict[str, str]
        Maps each section title (from SECTION_KEYS) to its content string.
    """
    result: dict[str, str] = {key: "" for key in SECTION_KEYS}

    # Build a pattern that matches any section heading regardless of number prefix
    # e.g. "## 3. Weaknesses" or "## Weaknesses"
    escaped_keys = [re.escape(k) for k in SECTION_KEYS]
    heading_pattern = re.compile(
        r"^#{1,3}\s+(?:\d+\.\s+)?(" + "|".join(escaped_keys) + r")\s*$",
        re.IGNORECASE | re.MULTILINE,
    )

    # Find all heading positions
    matches = list(heading_pattern.finditer(raw_markdown))
    if not matches:
        logger.warning("parse_sections: no recognisable section headings found in LLM output.")
        # Return the entire output under the first section as a fallback
        result[SECTION_KEYS[0]] = raw_markdown.strip()
        return result

    for i, match in enumerate(matches):
        # Canonical section name (from the regex capture group)
        raw_title = match.group(1).strip()
        canonical = next(
            (k for k in SECTION_KEYS if k.lower() == raw_title.lower()),
            raw_title,
        )

        # Content runs from end of this heading to start of next (or EOF)
        content_start = match.end()
        content_end   = matches[i + 1].start() if i + 1 < len(matches) else len(raw_markdown)
        content = raw_markdown[content_start:content_end].strip()

        # Remove a leading horizontal rule if the prompt injected one
        content = re.sub(r"^---\s*\n?", "", content).strip()

        if canonical in result:
            result[canonical] = content
        else:
            logger.debug("parse_sections: unrecognised section '%s' — skipped.", raw_title)

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Main inference function
# ─────────────────────────────────────────────────────────────────────────────

def analyze_resume(ctx: PromptContext) -> LLMReport:
    """
    Send resume + JD context to Llama3 via Ollama and return a parsed report.

    Parameters
    ----------
    ctx : PromptContext
        Populated by ``app.py`` from all earlier pipeline stages.

    Returns
    -------
    LLMReport
        ``success``      — False if Ollama is unreachable or errors out.
        ``raw_markdown`` — Complete LLM response for debugging.
        ``sections``     — Dict of section_title → markdown_content.
        ``error``        — Human-readable error message (empty on success).
        ``model``        — Model name that was used.
        ``duration_s``   — Wall-clock time in seconds.

    Notes
    -----
    * Uses ``ollama.chat`` with a system + user message pair.
    * Temperature 0.7 for creative but consistent output.
    * The ``num_ctx`` option extends the context window to handle
      longer resumes without silent truncation.
    """
    user_prompt = build_analysis_prompt(ctx)

    messages = [
        {"role": "system",  "content": SYSTEM_PROMPT},
        {"role": "user",    "content": user_prompt},
    ]

    logger.info(
        "analyze_resume: calling ollama.chat model=%s prompt_chars=%d",
        OLLAMA_MODEL, len(user_prompt),
    )

    start = time.time()

    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=messages,
            options={
                "temperature": 0.7,
                "num_ctx":     8192,     # expand context window
                "num_predict": 2048,     # max tokens to generate
            },
        )
    except ollama.ResponseError as exc:
        duration = round(time.time() - start, 2)
        msg = f"Ollama model error: {exc}"
        logger.error(msg)
        return LLMReport(
            success=False,
            raw_markdown="",
            sections={k: "" for k in SECTION_KEYS},
            error=msg,
            model=OLLAMA_MODEL,
            duration_s=duration,
        )
    except Exception as exc:
        duration = round(time.time() - start, 2)
        msg = (
            f"Could not reach Ollama ({exc}). "
            f"Make sure Ollama is running: ollama serve"
        )
        logger.error(msg)
        return LLMReport(
            success=False,
            raw_markdown="",
            sections={k: "" for k in SECTION_KEYS},
            error=msg,
            model=OLLAMA_MODEL,
            duration_s=duration,
        )

    duration = round(time.time() - start, 2)

    # Extract text — ollama 0.3.x returns a plain dict, not an object
    raw_markdown: str = response["message"]["content"] or ""

    logger.info(
        "analyze_resume: received %d chars in %.1fs",
        len(raw_markdown), duration,
    )

    if not raw_markdown.strip():
        return LLMReport(
            success=False,
            raw_markdown=raw_markdown,
            sections={k: "" for k in SECTION_KEYS},
            error="LLM returned an empty response. Try again.",
            model=OLLAMA_MODEL,
            duration_s=duration,
        )

    sections = parse_sections(raw_markdown)

    return LLMReport(
        success=True,
        raw_markdown=raw_markdown,
        sections=sections,
        error="",
        model=OLLAMA_MODEL,
        duration_s=duration,
    )
