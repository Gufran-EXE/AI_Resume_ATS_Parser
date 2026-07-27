# ============================================================
# modules/utils.py
#
# Responsibility: Shared text-preprocessing utilities.
#
# All functions in this file are pure (no side effects, no I/O)
# and safe to call from any other module.
#
# Public API
# ----------
# preprocess_text(text)          -> str   ← main entry point
#
# Individual pipeline steps (also importable for testing):
#   normalize_line_endings(text) -> str
#   remove_control_characters(text) -> str
#   fix_hyphenated_line_breaks(text) -> str
#   collapse_whitespace_in_lines(text) -> str
#   collapse_blank_lines(text)   -> str
# ============================================================

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pipeline steps
# Each function takes a str and returns a str.
# They are intentionally small so they are easy to test individually.
# ---------------------------------------------------------------------------


def normalize_line_endings(text: str) -> str:
    """
    Unify all line-ending variants to a plain ``\\n``.

    Handles:
    - Windows  ``\\r\\n``
    - Old Mac   ``\\r``
    - Form-feed ``\\f``  (common in PDFs at page boundaries)
    - Vertical tab ``\\v``
    """
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")
    text = text.replace("\f", "\n")
    text = text.replace("\v", "\n")
    return text


def remove_control_characters(text: str) -> str:
    """
    Strip non-printable control characters while keeping:
    - ``\\n``   (line feed — already normalised)
    - ``\\t``   (horizontal tab — used for indentation in some resumes)
    - Printable ASCII  (0x20 – 0x7E)
    - Extended Unicode printable characters (0xA0 and above)
      so that accented names, non-ASCII certifications, etc. survive.

    This step intentionally does NOT remove punctuation, slashes,
    plus signs, or any character meaningful in technical keywords
    (e.g. ``C++``, ``C#``, ``Node.js``, ``CI/CD``).
    """
    # Keep: tab (09), newline (0A), space–tilde (20–7E), non-ASCII printable (A0+)
    return re.sub(r"[^\x09\x0A\x20-\x7E\xA0-\uFFFF]", "", text)


def fix_hyphenated_line_breaks(text: str) -> str:
    """
    Re-join words that were split across lines with a hyphen by the PDF
    renderer (e.g. ``develop-\\nment`` → ``development``).

    Rule: merge only when the fragment before the hyphen is **5 or more**
    lowercase characters.  This avoids touching intentional hyphenated
    compounds where both halves are short, meaningful words
    (e.g. ``full-stack``, ``self-taught``, ``up-to-date``).
    """
    return re.sub(r"([a-z]{5,})-\n([a-z])", r"\1\2", text)


def collapse_whitespace_in_lines(text: str) -> str:
    """
    Within each line, collapse runs of spaces/tabs down to a single space
    and strip leading/trailing whitespace.

    Line breaks are preserved exactly — this step never removes ``\\n``.
    """
    lines = text.split("\n")
    cleaned = [re.sub(r"[ \t]+", " ", line).strip() for line in lines]
    return "\n".join(cleaned)


def collapse_blank_lines(text: str) -> str:
    """
    Reduce any run of more than one consecutive blank line to exactly one
    blank line.

    A single blank line between paragraphs/sections is kept as a natural
    visual separator that the LLM can use as a section boundary signal.
    """
    # Replace 3+ newlines (i.e. 2+ blank lines) with exactly 2 newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def preprocess_text(text: str) -> str:
    """
    Run the full preprocessing pipeline on raw extracted resume text.

    Pipeline (in order)
    -------------------
    1. ``normalize_line_endings``      — unify \\r\\n / \\r / \\f / \\v → \\n
    2. ``remove_control_characters``   — strip non-printable bytes
    3. ``fix_hyphenated_line_breaks``  — rejoin PDF-broken words
    4. ``collapse_whitespace_in_lines``— single space inside each line
    5. ``collapse_blank_lines``        — at most one blank line between blocks
    6. Final ``.strip()``              — remove leading / trailing whitespace

    Guarantees
    ----------
    - Punctuation is never removed (``.,;:!?()[]{}'"/-+#@&*``).
    - Technical tokens are preserved: ``C++``, ``C#``, ``Node.js``,
      ``CI/CD``, ``@decorator``, ``#tag``, version numbers like ``3.11``.
    - Accented and non-ASCII printable characters are preserved.
    - The result is a single clean UTF-8 string ready for LLM analysis.

    Parameters
    ----------
    text : str
        Raw text as returned by the PDF extraction engine.

    Returns
    -------
    str
        Cleaned text.  Empty string if input is empty or whitespace-only.
    """
    if not text or not text.strip():
        logger.debug("preprocess_text received empty input — returning empty string.")
        return ""

    original_len = len(text)

    text = normalize_line_endings(text)
    text = remove_control_characters(text)
    text = fix_hyphenated_line_breaks(text)
    text = collapse_whitespace_in_lines(text)
    text = collapse_blank_lines(text)
    text = text.strip()

    logger.debug(
        "preprocess_text: %d chars → %d chars (removed %d).",
        original_len,
        len(text),
        original_len - len(text),
    )

    return text
