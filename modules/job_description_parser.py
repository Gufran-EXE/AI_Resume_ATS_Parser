# ============================================================
# modules/job_description_parser.py
#
# Responsibility: Accept raw job-description text pasted by the
# user, clean it with the shared preprocessing pipeline, and
# return a structured JDResult ready for comparison.
#
# Public API
# ----------
# parse_job_description(raw_text: str) -> JDResult
#
# JDResult keys:
#   success    bool  – False only if the input is effectively empty
#   text       str   – cleaned full text
#   word_count int   – word count of cleaned text
#   error      str   – human-readable message (empty on success)
# ============================================================

from __future__ import annotations

import logging
from typing import TypedDict

from modules.utils import preprocess_text

logger = logging.getLogger(__name__)

# Minimum words we consider a parseable job description
_MIN_WORDS = 10


class JDResult(TypedDict):
    success: bool
    text: str
    word_count: int
    error: str


def parse_job_description(raw_text: str) -> JDResult:
    """
    Clean and structure a pasted job description.

    Parameters
    ----------
    raw_text : str
        The raw text typed or pasted by the user into the Streamlit
        text area.  May contain Windows line endings, stray whitespace,
        or copy-paste artefacts.

    Returns
    -------
    JDResult
        TypedDict with keys: success, text, word_count, error.

    Notes
    -----
    * Cleaning is delegated entirely to ``utils.preprocess_text`` so
      behaviour is identical to resume preprocessing.
    * No AI, no keyword extraction — this module only cleans and stores.
    * Keyword extraction is the responsibility of keyword_matcher.py.
    """
    if not raw_text or not raw_text.strip():
        logger.warning("parse_job_description received empty input.")
        return JDResult(
            success=False,
            text="",
            word_count=0,
            error="Job description is empty. Please paste the job description text.",
        )

    cleaned = preprocess_text(raw_text)
    word_count = len(cleaned.split())

    if word_count < _MIN_WORDS:
        logger.warning(
            "Job description too short after cleaning: %d words.", word_count
        )
        return JDResult(
            success=False,
            text=cleaned,
            word_count=word_count,
            error=(
                f"Job description is too short ({word_count} words). "
                "Please paste the full job description."
            ),
        )

    logger.info("parse_job_description: cleaned to %d words.", word_count)

    return JDResult(
        success=True,
        text=cleaned,
        word_count=word_count,
        error="",
    )
