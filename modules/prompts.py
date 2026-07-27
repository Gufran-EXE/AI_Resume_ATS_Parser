# ============================================================
# modules/prompts.py
#
# Responsibility: All LLM prompt templates in one place.
# No inference logic lives here — only string construction.
#
# Public API
# ----------
# build_analysis_prompt(context: PromptContext) -> str
#
# PromptContext (TypedDict)
#   resume_text    str
#   jd_text        str
#   matched_skills list[str]
#   missing_skills list[str]
#   ats_score      int
#   grade          str
#   match_pct      float
# ============================================================

from __future__ import annotations

from typing import TypedDict


# ─────────────────────────────────────────────────────────────────────────────
# Input context type
# ─────────────────────────────────────────────────────────────────────────────

class PromptContext(TypedDict):
    resume_text:    str
    jd_text:        str
    matched_skills: list[str]
    missing_skills: list[str]
    ats_score:      int
    grade:          str
    match_pct:      float


# ─────────────────────────────────────────────────────────────────────────────
# System prompt
# Sets the model's role, tone, and strict output contract.
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are an expert technical recruiter and career coach with 15+ years of \
experience in software engineering hiring. You specialise in ATS optimisation, \
resume writing, and career development.

Your task is to analyse a candidate's resume against a specific job description \
and produce a structured, honest, and actionable report.

OUTPUT RULES — follow these exactly:
1. Respond ONLY in the section format shown in the user message.
2. Use Markdown formatting inside each section (bullet points, bold, etc.).
3. Be specific and concrete — reference actual content from the resume and JD.
4. Do NOT invent skills or experience that are not in the resume.
5. Keep each section focused and professional.
6. Do NOT add extra sections or change the section headings.
7. Do NOT include any preamble, greeting, or closing remarks outside the sections.\
"""


# ─────────────────────────────────────────────────────────────────────────────
# User prompt builder
# ─────────────────────────────────────────────────────────────────────────────

def _fmt_list(items: list[str], fallback: str = "None identified") -> str:
    """Format a list as a comma-separated string, with a fallback for empty."""
    return ", ".join(items) if items else fallback


def _truncate(text: str, max_chars: int = 3000) -> str:
    """Trim long text to keep the prompt within a safe token budget."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n...[truncated for brevity]"


def build_analysis_prompt(ctx: PromptContext) -> str:
    """
    Build the full user-turn prompt from analysis context.

    The prompt injects:
    - ATS score, grade, and keyword match percentage
    - Matched and missing skill lists (pre-computed, no hallucination risk)
    - Truncated resume text (≤3000 chars)
    - Truncated job description (≤2000 chars)

    The seven required output sections are defined with explicit headings
    so the model output maps directly to the UI rendering functions.

    Parameters
    ----------
    ctx : PromptContext
        All data collected by the pipeline before calling the LLM.

    Returns
    -------
    str
        The complete user message to send to Llama3.
    """
    matched_str = _fmt_list(ctx["matched_skills"])
    missing_str = _fmt_list(ctx["missing_skills"])

    resume_snippet = _truncate(ctx["resume_text"], max_chars=3000)
    jd_snippet     = _truncate(ctx["jd_text"],     max_chars=2000)

    prompt = f"""\
## ATS ANALYSIS CONTEXT

**ATS Score:** {ctx["ats_score"]}/100  |  **Grade:** {ctx["grade"]}  |  **Keyword Match:** {ctx["match_pct"]:.1f}%

**Matched Skills ({len(ctx["matched_skills"])}):** {matched_str}

**Missing Skills ({len(ctx["missing_skills"])}):** {missing_str}

---

## RESUME TEXT

{resume_snippet}

---

## JOB DESCRIPTION

{jd_snippet}

---

## YOUR TASK

Analyse the resume against the job description using the context above.
Produce the report in EXACTLY these nine sections with these EXACT headings:

---

## 1. Overall Resume Review
[2-4 sentences giving an honest overall assessment of how well this resume \
fits the role. Mention the ATS score and what it signals.]

## 2. Strengths
[3-5 bullet points highlighting what the candidate does well relative to \
the job requirements. Be specific — reference actual skills or experience.]

## 3. Weaknesses
[3-5 bullet points identifying the main gaps or weak areas. Reference the \
missing skills and any structural or content problems.]

## 4. Missing Technical Skills
[Bullet list of the specific technical skills from the JD that are absent \
from the resume. For each, add one sentence explaining why it matters for \
this role.]

## 5. Suggestions for Improvement
[5-7 concrete, actionable bullet points the candidate can act on immediately \
to improve this resume for this specific role.]

## 6. Resume Summary
[Write a 3-4 sentence professional summary the candidate could add to the \
top of their resume, tailored to this specific job description.]

## 7. Career Advice
[2-3 bullet points of broader career advice — skills to learn, certifications \
to pursue, or strategies to become a stronger candidate for this type of role.]

## 8. Improved Bullet Points
[Select 2-3 bullet points from the resume and rewrite them using the Action-Context-Result (or XYZ) format to make them significantly more impactful for this job description.]

## 9. Interview Questions
[Provide 2-3 potential interview questions based on the resume gaps, along with short suggested talking points or answers for the candidate.]
"""
    return prompt
