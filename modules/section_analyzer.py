# ============================================================
# modules/section_analyzer.py
#
# Responsibility: Detect the presence and quality of standard
# resume sections using header keyword matching and content
# heuristics. No LLM — pure rule-based analysis.
#
# Public API
# ----------
# analyze_sections(resume_text: str) -> SectionAnalysis
#
# SectionAnalysis (TypedDict)
#   sections  dict[str, SectionStatus]
#   present   list[str]
#   missing   list[str]
#   weak      list[str]
#   score     int        — 0-100 completeness score
#
# SectionStatus (TypedDict)
#   status   str    — "present" | "missing" | "needs_improvement"
#   found_header str | None
#   word_count   int
#   recommendation str
# ============================================================

from __future__ import annotations

import logging
import re
from typing import TypedDict

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Section definitions
# Each entry has:
#   headers      — lowercase trigger words that identify this section
#   min_words    — below this content word count → "needs_improvement"
#   weight       — importance weight for the completeness score (must sum ~100)
#   missing_rec  — advice if section is absent
#   weak_rec     — advice if section content is thin
# ─────────────────────────────────────────────────────────────────────────────

_SECTION_DEFS: dict[str, dict] = {
    "Experience": {
        "headers": [
            "experience", "work experience", "professional experience",
            "employment", "work history", "career history",
            "internship", "internships",
        ],
        "min_words": 20,
        "weight": 25,
        "missing_rec": (
            "Add a Work Experience section with role titles, company names, "
            "dates, and 2-4 achievement-oriented bullet points per role."
        ),
        "weak_rec": (
            "Your Experience section is thin. Add quantified bullet points "
            "(e.g. 'Reduced API latency by 30%') to strengthen it."
        ),
    },
    "Skills": {
        "headers": [
            "skills", "technical skills", "core competencies",
            "competencies", "key skills", "technologies",
            "tools", "tech stack", "technical expertise",
        ],
        "min_words": 8,
        "weight": 20,
        "missing_rec": (
            "Add a Skills section listing your programming languages, "
            "frameworks, databases, and tools — ATS systems scan this directly."
        ),
        "weak_rec": (
            "Skills section looks sparse. Expand it with specific tools, "
            "libraries, and technologies grouped by category."
        ),
    },
    "Education": {
        "headers": [
            "education", "academic background", "academic history",
            "qualifications", "degrees", "university", "college",
            "school",
        ],
        "min_words": 10,
        "weight": 15,
        "missing_rec": (
            "Add an Education section with your degree, institution, "
            "graduation year, and any relevant coursework or GPA."
        ),
        "weak_rec": (
            "Education section is minimal. Include degree name, institution, "
            "year, and any honours or relevant modules."
        ),
    },
    "Projects": {
        "headers": [
            "projects", "personal projects", "academic projects",
            "side projects", "portfolio", "open source",
            "github projects",
        ],
        "min_words": 8,
        "weight": 15,
        "missing_rec": (
            "Add a Projects section. Employers value practical work — "
            "include 2-3 projects with tech stack, your role, and outcomes."
        ),
        "weak_rec": (
            "Projects section is underdeveloped. Add links, tech stacks, "
            "and a one-line impact statement per project."
        ),
    },
    "Certifications": {
        "headers": [
            "certifications", "certification", "certificates",
            "licenses", "accreditations", "credentials",
            "professional development",
        ],
        "min_words": 5,
        "weight": 10,
        "missing_rec": (
            "Consider adding a Certifications section. Even one relevant "
            "certification (e.g. AWS, Google Cloud) signals commitment."
        ),
        "weak_rec": (
            "Certifications section exists but is thin. Add certification "
            "name, issuing body, and year obtained."
        ),
    },
    "Achievements": {
        "headers": [
            "achievements", "accomplishments", "awards",
            "honours", "honors", "recognition",
            "publications", "speaking", "volunteer",
        ],
        "min_words": 4,
        "weight": 10,
        "missing_rec": (
            "An Achievements or Awards section can differentiate you. "
            "Include hackathon wins, publications, or notable recognitions."
        ),
        "weak_rec": (
            "Achievements section is minimal. Add specific results, dates, "
            "and the context that makes each achievement meaningful."
        ),
    },
    "Summary": {
        "headers": [
            "summary", "professional summary", "profile",
            "objective", "career objective", "about me",
            "overview", "professional profile",
        ],
        "min_words": 8,
        "weight": 5,
        "missing_rec": (
            "Add a 3-4 sentence Professional Summary at the top tailored "
            "to the role — this is the first thing recruiters read."
        ),
        "weak_rec": (
            "Your summary is too brief. Expand to 3-4 sentences covering "
            "your experience level, key skills, and career goal."
        ),
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Return types
# ─────────────────────────────────────────────────────────────────────────────

class SectionStatus(TypedDict):
    status:         str          # "present" | "missing" | "needs_improvement"
    found_header:   str | None   # actual header text found in the resume
    word_count:     int          # approximate words in this section's content
    recommendation: str          # what to do


class SectionAnalysis(TypedDict):
    sections: dict[str, SectionStatus]
    present:  list[str]   # section names with status "present"
    missing:  list[str]   # section names with status "missing"
    weak:     list[str]   # section names with status "needs_improvement"
    score:    int         # 0-100 completeness score


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _find_section_header(text_lower: str, headers: list[str]) -> str | None:
    """
    Search for any of the given header strings in the resume text.

    Uses MULTILINE mode so ^ and $ match line boundaries.
    A match is valid when the header appears at the start of a line
    (optionally with leading whitespace) and is followed by end-of-line,
    a colon, or whitespace — preventing false positives inside sentences.
    Returns None if no match is found or the matched text is empty.
    """
    for header in headers:
        pattern = re.compile(
            r"^\s*" + re.escape(header) + r"\s*(?::|$)",
            re.IGNORECASE | re.MULTILINE,
        )
        m = pattern.search(text_lower)
        if m:
            # Return the matched line stripped of surrounding whitespace and colons
            cleaned = m.group(0).strip().strip(":")
            if cleaned:
                return cleaned
    return None


def _count_words_after_header(
    text: str,
    header_start_pos: int,
    next_section_pos: int,
) -> int:
    """Count words in the content *after* the header line."""
    # Skip to the end of the header line first
    newline_pos = text.find("\n", header_start_pos)
    if newline_pos == -1:
        return 0
    content = text[newline_pos:next_section_pos]
    return len(content.split())


def _find_all_header_positions(text_lower: str) -> list[tuple[int, str]]:
    """
    Return a sorted list of (position, section_name) for every detected
    section header. Position points to the START of the header word
    (not any preceding newline), so content slicing is accurate.
    """
    positions: list[tuple[int, str]] = []
    for section_name, defn in _SECTION_DEFS.items():
        for header in defn["headers"]:
            pattern = re.compile(
                r"^\s*" + re.escape(header) + r"\s*(?::|$)",
                re.IGNORECASE | re.MULTILINE,
            )
            m = pattern.search(text_lower)
            if m:
                # Skip any leading \n so position is on the header word itself
                pos = m.start()
                while pos < len(text_lower) and text_lower[pos] in ('\n', '\r', ' ', '\t'):
                    pos += 1
                positions.append((pos, section_name))
                break
    return sorted(positions, key=lambda x: x[0])


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def analyze_sections(resume_text: str) -> SectionAnalysis:
    """
    Detect the presence and quality of standard resume sections.

    Parameters
    ----------
    resume_text : str
        Cleaned resume text from ``resume_parser.parse_resume()``.

    Returns
    -------
    SectionAnalysis
        Per-section statuses, plus ``present``, ``missing``, ``weak``
        lists and an overall ``score`` (0-100).

    Notes
    -----
    * Detection uses line-anchored header matching — avoids false positives
      when words like "experience" appear mid-sentence.
    * Content word count is estimated by slicing between adjacent headers.
    * A section is "needs_improvement" if found but content is thin
      (below the per-section ``min_words`` threshold).
    """
    text_lower = resume_text.lower()

    # Get all header positions for content slicing
    all_positions = _find_all_header_positions(text_lower)
    pos_map: dict[str, int] = {name: pos for pos, name in all_positions}

    sections: dict[str, SectionStatus] = {}
    present:  list[str] = []
    missing:  list[str] = []
    weak:     list[str] = []
    score_total = 0.0

    for section_name, defn in _SECTION_DEFS.items():
        found_header = _find_section_header(text_lower, defn["headers"])

        if found_header is None:
            # Section not found
            sections[section_name] = SectionStatus(
                status="missing",
                found_header=None,
                word_count=0,
                recommendation=defn["missing_rec"],
            )
            missing.append(section_name)
            # No score contribution
            continue

        # Section found — estimate content word count
        start_pos = pos_map.get(section_name, 0)
        # Find next section header position
        next_pos = len(resume_text)
        for pos, name in all_positions:
            if pos > start_pos and name != section_name:
                next_pos = pos
                break

        word_count = _count_words_after_header(resume_text, start_pos, next_pos)

        if word_count < defn["min_words"]:
            status = "needs_improvement"
            rec    = defn["weak_rec"]
            weak.append(section_name)
            # Partial score contribution
            score_total += defn["weight"] * 0.5
        else:
            status = "present"
            rec    = ""
            present.append(section_name)
            score_total += defn["weight"]

        sections[section_name] = SectionStatus(
            status=status,
            found_header=found_header,
            word_count=word_count,
            recommendation=rec,
        )

    overall_score = max(0, min(100, round(score_total)))

    logger.info(
        "analyze_sections: present=%d missing=%d weak=%d score=%d",
        len(present), len(missing), len(weak), overall_score,
    )

    return SectionAnalysis(
        sections=sections,
        present=present,
        missing=missing,
        weak=weak,
        score=overall_score,
    )
