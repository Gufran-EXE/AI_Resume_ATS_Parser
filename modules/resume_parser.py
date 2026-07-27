# ============================================================
# modules/resume_parser.py
#
# Responsibility: Extract and clean raw text from a PDF resume.
#
# Primary engine : pdfplumber  (accurate layout-aware extraction)
# Fallback engine: PyPDF2      (used when pdfplumber yields nothing)
#
# Public API (what the rest of the app imports):
#   parse_resume(file)  ->  ParseResult  (TypedDict)
#
# ParseResult keys:
#   success      bool   – True if usable text was extracted
#   text         str    – full cleaned text (empty string on failure)
#   page_count   int    – number of pages found
#   word_count   int    – word count of extracted text
#   error        str    – human-readable error message (empty on success)
#   engine       str    – "pdfplumber" | "PyPDF2" | "none"
# ============================================================

from __future__ import annotations

import io
import logging
from typing import TypedDict

import pdfplumber
import PyPDF2

from modules.utils import preprocess_text

# ── Module-level logger (does not touch the root logger) ────────────────────
logger = logging.getLogger(__name__)

# ── Minimum character threshold to consider extraction successful ────────────
_MIN_CHARS = 50


# ── Return type ─────────────────────────────────────────────────────────────
class ParseResult(TypedDict):
    success: bool
    text: str
    page_count: int
    word_count: int
    error: str
    engine: str


# ── Helpers ─────────────────────────────────────────────────────────────────


def _make_error(message: str, page_count: int = 0) -> ParseResult:
    """Return a failed ParseResult with a descriptive error message."""
    logger.error("resume_parser error: %s", message)
    return ParseResult(
        success=False,
        text="",
        page_count=page_count,
        word_count=0,
        error=message,
        engine="none",
    )


# ── Primary extractor: pdfplumber ───────────────────────────────────────────

def _extract_with_pdfplumber(file_bytes: bytes) -> tuple[str, int]:
    """
    Extract text from all pages using pdfplumber.

    Returns:
        (raw_text, page_count)

    Raises:
        Exception – re-raises any pdfplumber error so the caller can fall back.
    """
    pages_text: list[str] = []

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        page_count = len(pdf.pages)

        for page_num, page in enumerate(pdf.pages, start=1):
            try:
                page_text = page.extract_text() or ""
                pages_text.append(page_text)
                logger.debug("pdfplumber — page %d: %d chars", page_num, len(page_text))
            except Exception as exc:  # noqa: BLE001
                # One bad page should not abort the whole document
                logger.warning(
                    "pdfplumber failed on page %d (%s). Skipping.", page_num, exc
                )
                pages_text.append("")

    return "\n\n".join(pages_text), page_count


# ── Fallback extractor: PyPDF2 ───────────────────────────────────────────────

def _extract_with_pypdf2(file_bytes: bytes) -> tuple[str, int]:
    """
    Extract text from all pages using PyPDF2.

    Returns:
        (raw_text, page_count)

    Raises:
        Exception – re-raises any PyPDF2 error so the caller can report it.
    """
    pages_text: list[str] = []
    reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
    page_count = len(reader.pages)

    for page_num, page in enumerate(reader.pages, start=1):
        try:
            page_text = page.extract_text() or ""
            pages_text.append(page_text)
            logger.debug("PyPDF2 — page %d: %d chars", page_num, len(page_text))
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "PyPDF2 failed on page %d (%s). Skipping.", page_num, exc
            )
            pages_text.append("")

    return "\n\n".join(pages_text), page_count


# ── Public API ───────────────────────────────────────────────────────────────

def parse_resume(file) -> ParseResult:
    """
    Extract all readable text from a PDF resume.

    Parameters
    ----------
    file : file-like object
        A Streamlit ``UploadedFile`` or any binary file-like object whose
        ``.read()`` method returns bytes.

    Returns
    -------
    ParseResult
        TypedDict with keys: success, text, page_count, word_count,
        error, engine.

    Notes
    -----
    * Multi-page PDFs are fully supported; pages are joined with a blank line.
    * pdfplumber is tried first.  If it produces fewer than ``_MIN_CHARS``
      characters, PyPDF2 is tried as a fallback.
    * Per-page exceptions are logged and skipped rather than aborting the run.
    * The returned ``text`` is always a cleaned, printable UTF-8 string.
    """
    # ── 1. Read bytes once so both engines share the same buffer ────────────
    try:
        file_bytes: bytes = file.read()
    except Exception as exc:
        return _make_error(f"Could not read the uploaded file: {exc}")

    if not file_bytes:
        return _make_error("The uploaded file is empty.")

    # ── 2. Basic PDF magic-number check (PDF starts with %PDF) ──────────────
    if not file_bytes.startswith(b"%PDF"):
        return _make_error(
            "The file does not appear to be a valid PDF. "
            "Please upload a PDF document."
        )

    # ── 3. Try pdfplumber ────────────────────────────────────────────────────
    raw_text = ""
    page_count = 0
    engine_used = "none"

    try:
        raw_text, page_count = _extract_with_pdfplumber(file_bytes)
        engine_used = "pdfplumber"
        logger.info(
            "pdfplumber extracted %d chars across %d pages.", len(raw_text), page_count
        )
    except Exception as exc:
        logger.warning("pdfplumber failed entirely (%s). Trying PyPDF2.", exc)

    # ── 4. Fall back to PyPDF2 if pdfplumber gave too little text ────────────
    if len(raw_text.strip()) < _MIN_CHARS:
        logger.info(
            "pdfplumber result too short (%d chars). Attempting PyPDF2 fallback.",
            len(raw_text.strip()),
        )
        try:
            fallback_text, fallback_pages = _extract_with_pypdf2(file_bytes)
            if len(fallback_text.strip()) > len(raw_text.strip()):
                raw_text = fallback_text
                page_count = fallback_pages
                engine_used = "PyPDF2"
                logger.info(
                    "PyPDF2 fallback succeeded: %d chars across %d pages.",
                    len(raw_text),
                    page_count,
                )
        except Exception as exc:
            logger.error("PyPDF2 fallback also failed: %s", exc)
            # page_count may still be 0; keep whatever pdfplumber gave us

    # ── 5. Final check — did we get anything usable? ─────────────────────────
    if len(raw_text.strip()) < _MIN_CHARS:
        return _make_error(
            "No readable text could be extracted from this PDF. "
            "It may be a scanned image or a heavily formatted document. "
            "Try saving your resume as a plain-text PDF and re-uploading.",
            page_count=page_count,
        )

    # ── 6. Clean and return ──────────────────────────────────────────────────
    clean = preprocess_text(raw_text)
    word_count = len(clean.split())

    logger.info(
        "parse_resume complete — engine=%s pages=%d words=%d",
        engine_used,
        page_count,
        word_count,
    )

    return ParseResult(
        success=True,
        text=clean,
        page_count=page_count,
        word_count=word_count,
        error="",
        engine=engine_used,
    )
