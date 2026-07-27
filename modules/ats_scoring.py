# ============================================================
# modules/ats_scoring.py
#
# Responsibility: Calculate an ATS-style compatibility score
# from the keyword match data produced by keyword_matcher.py.
# No LLM, no AI — pure rule-based arithmetic.
#
# Scoring model (100 points total)
# ---------------------------------
#  Component            Max pts  Source
#  ─────────────────────────────────────────────────────────
#  Keyword Match Score   55      % of JD keywords in resume
#  Coverage Bonus        15      how many JD categories covered
#  Depth Bonus           15      total matched keyword count
#  Soft-Skills Score     15      soft-skill keyword overlap
#  ─────────────────────────────────────────────────────────
#  Total                100
#
# Public API
# ----------
# calculate_ats_score(match, resume_kw, jd_kw) -> ATSResult
#
# ATSResult (TypedDict)
#   total_score    int            0-100, rounded
#   grade          str            A+ / A / A- / B+ … F
#   status         str            "PASS" | "FAIL"
#   breakdown      ScoreBreakdown
#   matched_count  int
#   missing_count  int
#   total_jd_kw    int
#   match_pct      float
# ============================================================

from __future__ import annotations

import logging
from typing import TypedDict

from modules.keyword_matcher import KeywordResult, MatchResult

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Scoring constants
# ─────────────────────────────────────────────────────────────────────────────

# Component maximums (must sum to 100)
_MAX_KEYWORD   = 55   # raw keyword overlap percentage contribution
_MAX_COVERAGE  = 15   # breadth: how many JD skill categories are covered
_MAX_DEPTH     = 15   # depth: total number of matched keywords (capped)
_MAX_SOFT      = 15   # soft-skill keyword overlap

# Passing threshold
PASSING_SCORE = 70

# Depth bonus: one point per matched keyword up to this cap
_DEPTH_CAP = 20   # 20+ matched keywords → full depth bonus

# Grade bands: (minimum_score_to_reach_this_grade, label)
# Evaluated highest-first — first band where score >= minimum wins.
_GRADE_BANDS: list[tuple[int, str]] = [
    (95, "A+"),
    (90, "A"),
    (85, "A-"),
    (80, "B+"),
    (75, "B"),
    (70, "B-"),
    (65, "C+"),
    (60, "C"),
    (50, "C-"),
    (40, "D"),
    (0,  "F"),
]

# Soft-skill category name — must match the key in KEYWORD_TAXONOMY
_SOFT_SKILL_CATEGORY = "Soft Skills"


# ─────────────────────────────────────────────────────────────────────────────
# Return types
# ─────────────────────────────────────────────────────────────────────────────

class ScoreBreakdown(TypedDict):
    keyword_score:  float   # 0 – _MAX_KEYWORD
    coverage_score: float   # 0 – _MAX_COVERAGE
    depth_score:    float   # 0 – _MAX_DEPTH
    soft_score:     float   # 0 – _MAX_SOFT
    keyword_max:    int
    coverage_max:   int
    depth_max:      int
    soft_max:       int


class ATSResult(TypedDict):
    total_score:   int
    grade:         str
    status:        str
    breakdown:     ScoreBreakdown
    matched_count: int
    missing_count: int
    total_jd_kw:   int
    match_pct:     float


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _assign_grade(score: int) -> str:
    """Map a 0-100 integer score to a letter grade.

    Bands are minimum-inclusive: score 95 → A+, score 90 → A, etc.
    Evaluated from highest threshold downward; first match wins.
    """
    for minimum, grade in _GRADE_BANDS:          # already sorted high→low
        if score >= minimum:
            return grade
    return "F"


def _keyword_component(match_pct: float) -> float:
    """
    Convert keyword match percentage to a score out of _MAX_KEYWORD.

    Uses a mild square-root curve so that moderate matches (40-60 %)
    still score meaningfully, while very high matches are rewarded.
    """
    import math
    clamped = max(0.0, min(100.0, match_pct))
    # Linear: direct proportion of max points
    linear = (clamped / 100.0) * _MAX_KEYWORD
    return round(linear, 2)


def _coverage_component(
    resume_kw: KeywordResult,
    jd_kw: KeywordResult,
) -> float:
    """
    Score based on how many distinct skill *categories* from the JD
    the resume covers.

    e.g. if the JD mentions skills in 4 categories and the resume
    covers 3 of them → 3/4 × _MAX_COVERAGE.
    """
    jd_cats = set(jd_kw["by_category"].keys())
    if not jd_cats:
        return 0.0

    resume_cats = set(resume_kw["by_category"].keys())
    covered = len(jd_cats & resume_cats)
    score = (covered / len(jd_cats)) * _MAX_COVERAGE
    return round(score, 2)


def _depth_component(matched_count: int) -> float:
    """
    Score based on the raw count of matched keywords, capped at _DEPTH_CAP.

    Rewards resumes that match many keywords, not just a high percentage.
    """
    capped = min(matched_count, _DEPTH_CAP)
    score = (capped / _DEPTH_CAP) * _MAX_DEPTH
    return round(score, 2)


def _soft_skill_component(
    resume_kw: KeywordResult,
    jd_kw: KeywordResult,
) -> float:
    """
    Score soft-skill keyword overlap independently.

    Soft skills are weighted separately because many ATS systems give
    extra credit for interpersonal / process keywords that signal culture fit.

    Rules:
    - If the JD has no keywords at all (empty input) → 0 points (nothing to reward).
    - If the JD has keywords but none are soft skills → full marks awarded
      (not the resume's fault the JD didn't list soft skills).
    - Otherwise → proportional score based on soft-skill overlap.
    """
    jd_soft  = set(jd_kw["by_category"].get(_SOFT_SKILL_CATEGORY, []))
    res_soft = set(resume_kw["by_category"].get(_SOFT_SKILL_CATEGORY, []))

    # JD is completely empty — no bonus
    if not jd_kw["all_keywords"]:
        return 0.0

    # JD has technical content but no soft-skill requirements → full marks
    if not jd_soft:
        return float(_MAX_SOFT)

    matched_soft = len(jd_soft & res_soft)
    score = (matched_soft / len(jd_soft)) * _MAX_SOFT
    return round(score, 2)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def calculate_ats_score(
    match: MatchResult,
    resume_kw: KeywordResult,
    jd_kw: KeywordResult,
) -> ATSResult:
    """
    Calculate a composite ATS compatibility score.

    Parameters
    ----------
    match : MatchResult
        Output of ``keyword_matcher.match_keywords()``.
    resume_kw : KeywordResult
        Output of ``keyword_matcher.extract_keywords()`` on the resume.
    jd_kw : KeywordResult
        Output of ``keyword_matcher.extract_keywords()`` on the JD.

    Returns
    -------
    ATSResult
        Full scoring result including total score, grade, PASS/FAIL
        status, per-component breakdown, and count statistics.

    Notes
    -----
    * No LLM or AI is involved — pure arithmetic on keyword data.
    * All component scores are capped at their respective maximums.
    * ``total_score`` is rounded to the nearest integer, clamped 0-100.
    """
    # ── Component scores ─────────────────────────────────────────────────────
    kw_score  = _keyword_component(match["match_pct"])
    cov_score = _coverage_component(resume_kw, jd_kw)
    dep_score = _depth_component(len(match["matched"]))
    soft_score = _soft_skill_component(resume_kw, jd_kw)

    raw_total = kw_score + cov_score + dep_score + soft_score
    total = max(0, min(100, round(raw_total)))

    grade  = _assign_grade(total)
    status = "PASS" if total >= PASSING_SCORE else "FAIL"

    breakdown = ScoreBreakdown(
        keyword_score  = kw_score,
        coverage_score = cov_score,
        depth_score    = dep_score,
        soft_score     = soft_score,
        keyword_max    = _MAX_KEYWORD,
        coverage_max   = _MAX_COVERAGE,
        depth_max      = _MAX_DEPTH,
        soft_max        = _MAX_SOFT,
    )

    logger.info(
        "calculate_ats_score: total=%d grade=%s status=%s "
        "(kw=%.1f cov=%.1f dep=%.1f soft=%.1f)",
        total, grade, status,
        kw_score, cov_score, dep_score, soft_score,
    )

    return ATSResult(
        total_score   = total,
        grade         = grade,
        status        = status,
        breakdown     = breakdown,
        matched_count = len(match["matched"]),
        missing_count = len(match["missing"]),
        total_jd_kw   = len(jd_kw["all_keywords"]),
        match_pct     = match["match_pct"],
    )
