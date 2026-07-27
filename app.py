
# ============================================================
# app.py  —  AI Resume Optimizer & ATS Analyzer
# Streamlit frontend — UI only (no AI logic yet)
# ============================================================

import streamlit as st
from config.settings import (
    APP_TITLE, APP_SUBTITLE, APP_ICON,
    AUTHOR, SIDEBAR_DESCRIPTION, TECH_STACK,
    JD_PLACEHOLDER, MAX_PDF_SIZE_MB, MIN_JD_WORDS,
    SCORE_COLOR_HIGH, SCORE_COLOR_MEDIUM, SCORE_COLOR_LOW,
    PASSING_ATS_SCORE,
    ATS_MAX_KEYWORD, ATS_MAX_COVERAGE, ATS_MAX_DEPTH, ATS_MAX_SOFT,
)
from modules.resume_parser import parse_resume, ParseResult
from modules.job_description_parser import parse_job_description, JDResult
from modules.keyword_matcher import (
    extract_keywords, match_keywords, KeywordResult, MatchResult,
)
from modules.ats_scoring import calculate_ats_score, ATSResult
from modules.prompts import PromptContext
from modules.llm_analyzer import (
    analyze_resume as llm_analyze,
    check_ollama_connection,
    LLMReport,
    SECTION_KEYS,
)
from modules.skill_recommender import recommend_skills, SkillRecommendations
from modules.section_analyzer import analyze_sections, SectionAnalysis
from modules.pdf_generator import generate_pdf_report

# ─────────────────────────────────────────────
# Page configuration  (must be first Streamlit call)
# ─────────────────────────────────────────────
st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# Global CSS
# ─────────────────────────────────────────────
def inject_css() -> None:
    st.markdown(
        """
        <style>
        /* ── Base & font ── */
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap');

        html, body, [class*="css"] {
            font-family: 'Outfit', sans-serif;
            color: #f3f4f6;
        }

        /* ── Hide default Streamlit chrome ── */
        #MainMenu, footer { visibility: hidden; }
        header { visibility: hidden; }

        /* ── App background ── */
        .stApp {
            background: linear-gradient(135deg, #0b0f19 0%, #111827 50%, #1e1b4b 100%);
            color: #f3f4f6;
        }

        /* ── Sidebar ── */
        [data-testid="stSidebar"] {
            background: rgba(9, 11, 20, 0.96) !important;
            border-right: 1px solid rgba(255, 255, 255, 0.05);
        }
        [data-testid="stSidebar"] * { color: #d1d5db !important; }
        [data-testid="stSidebar"] hr { border-top-color: rgba(255, 255, 255, 0.06) !important; }

        /* ── Cards ── */
        .card {
            background: rgba(17, 24, 39, 0.65);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 16px;
            padding: 1.5rem 1.8rem;
            margin-bottom: 1.2rem;
            backdrop-filter: blur(12px);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
            transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1), 
                        border-color 0.25s cubic-bezier(0.4, 0, 0.2, 1),
                        box-shadow 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .card:hover {
            transform: translateY(-2px);
            border-color: rgba(139, 92, 246, 0.25);
            box-shadow: 0 12px 40px 0 rgba(139, 92, 246, 0.12);
        }

        /* ── Section headings inside cards ── */
        .card h3 {
            margin-top: 0;
            font-size: 1.1rem;
            font-weight: 600;
            color: #c084fc;
            letter-spacing: 0.3px;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        /* ── Hero title ── */
        .hero-title {
            font-size: 2.8rem;
            font-weight: 800;
            background: linear-gradient(90deg, #c084fc 0%, #818cf8 50%, #38bdf8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            line-height: 1.15;
            margin-bottom: 0.3rem;
            letter-spacing: -0.5px;
        }
        .hero-subtitle {
            font-size: 1.1rem;
            color: #9ca3af;
            margin-bottom: 0;
        }

        /* ── Primary Analyze button ── */
        div[data-testid="stButton"] > button {
            background: linear-gradient(135deg, #8b5cf6 0%, #4f46e5 100%) !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 12px !important;
            padding: 0.75rem 2rem !important;
            font-size: 1.05rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.5px !important;
            box-shadow: 0 4px 15px rgba(139, 92, 246, 0.2) !important;
            transition: all 0.2s ease !important;
            width: 100% !important;
        }
        div[data-testid="stButton"] > button:hover {
            transform: translateY(-1px) !important;
            box-shadow: 0 6px 20px rgba(139, 92, 246, 0.35) !important;
            opacity: 0.95 !important;
        }
        div[data-testid="stButton"] > button:active {
            transform: translateY(1px) !important;
        }

        /* ── Download PDF button ── */
        div[data-testid="stDownloadButton"] > button {
            background: linear-gradient(135deg, #059669 0%, #10b981 100%) !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 12px !important;
            padding: 0.6rem 1.6rem !important;
            font-size: 0.95rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.3px !important;
            box-shadow: 0 4px 14px rgba(16, 185, 129, 0.2) !important;
            transition: all 0.2s ease !important;
            width: 100% !important;
        }
        div[data-testid="stDownloadButton"] > button:hover {
            transform: translateY(-1px) !important;
            box-shadow: 0 6px 18px rgba(16, 185, 129, 0.35) !important;
            opacity: 0.95 !important;
        }

        /* ── Custom Scrollable text preview block ── */
        .preview-box {
            background: rgba(0, 0, 0, 0.45) !important;
            border: 1px solid rgba(255, 255, 255, 0.05) !important;
            border-radius: 10px !important;
            padding: 1.2rem !important;
            font-size: 0.85rem !important;
            color: #cbd5e1 !important;
            font-family: 'JetBrains Mono', monospace !important;
            max-height: 280px !important;
            overflow-y: auto !important;
            line-height: 1.7 !important;
        }

        /* ── Custom scrollbars ── */
        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }
        ::-webkit-scrollbar-track {
            background: rgba(0, 0, 0, 0.05);
        }
        ::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: rgba(255, 255, 255, 0.25);
        }

        /* ── Streamlit Expanders override ── */
        div[data-testid="stExpander"] {
            background: rgba(17, 24, 39, 0.3) !important;
            border: 1px solid rgba(255, 255, 255, 0.05) !important;
            border-radius: 12px !important;
            margin-top: 0.5rem !important;
        }

        /* ── Score ring wrapper ── */
        .score-ring-wrap {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 1rem 0 0.5rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────
def render_sidebar() -> None:
    with st.sidebar:
        st.markdown("## 🎯 About This App")
        st.markdown(f"<p style='font-size:0.9rem;line-height:1.6'>{SIDEBAR_DESCRIPTION}</p>",
                    unsafe_allow_html=True)

        st.divider()

        st.markdown("## 🛠️ Tech Stack")
        for icon, name in TECH_STACK:
            st.markdown(
                f"<div style='display:flex;align-items:center;gap:0.5rem;"
                f"padding:0.35rem 0;font-size:0.9rem'>"
                f"<span style='font-size:1.1rem'>{icon}</span> {name}</div>",
                unsafe_allow_html=True,
            )

        st.divider()

        st.markdown("## ⚡ How It Works")
        steps = [
            ("1", "Upload your resume PDF"),
            ("2", "Paste the job description"),
            ("3", "Click **Analyze Resume**"),
            ("4", "Review your ATS score & AI suggestions"),
        ]
        for num, step in steps:
            st.markdown(
                f"<div style='display:flex;gap:0.7rem;align-items:flex-start;"
                f"padding:0.3rem 0;font-size:0.88rem'>"
                f"<span style='background:rgba(139,92,246,0.25);color:#c084fc;"
                f"border-radius:50%;width:1.4rem;height:1.4rem;display:flex;"
                f"align-items:center;justify-content:center;flex-shrink:0;"
                f"font-weight:700;font-size:0.75rem'>{num}</span>"
                f"<span>{step}</span></div>",
                unsafe_allow_html=True,
            )

        st.divider()

        st.markdown(
            "<p style='font-size:0.78rem;color:#9ca3af;text-align:center'>"
            "Runs 100% locally — your data never leaves your machine.</p>",
            unsafe_allow_html=True,
        )

        # ── Ollama connection status ─────────────────────────────────────
        st.divider()
        status = check_ollama_connection()
        if status["available"] and status["model_ready"]:
            st.markdown(
                "<div style='display:flex;align-items:center;gap:0.5rem;"
                "font-size:0.82rem;color:#10b981'>"
                "<span style='width:8px;height:8px;border-radius:50%;"
                "background:#10b981;flex-shrink:0'></span>"
                "Ollama · Llama3 ready</div>",
                unsafe_allow_html=True,
            )
        elif status["available"] and not status["model_ready"]:
            st.markdown(
                "<div style='font-size:0.8rem;color:#f59e0b'>"
                "⚠️ Ollama running but Llama3 not pulled.<br>"
                "<code style='font-size:0.75rem'>ollama pull llama3</code>"
                "</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div style='font-size:0.8rem;color:#ef4444'>"
                "🔴 Ollama not running.<br>"
                "<code style='font-size:0.75rem'>ollama serve</code>"
                "</div>",
                unsafe_allow_html=True,
            )

# ─────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────
def render_header() -> None:
    st.markdown(
        f"<div class='hero-title'>{APP_ICON} {APP_TITLE}</div>"
        f"<div class='hero-subtitle'>{APP_SUBTITLE}</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div style='margin-bottom:1.5rem'></div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Input Section
# ─────────────────────────────────────────────
def render_inputs() -> tuple:
    """
    Renders the resume upload and job description input widgets.
    Returns (uploaded_file, job_description_text).
    """
    col_left, col_right = st.columns(2, gap="large")

    # ── Left: Resume Upload ──────────────────
    with col_left:
        st.markdown(
            "<div class='card'>"
            "<h3>📄 Upload Resume</h3>",
            unsafe_allow_html=True,
        )
        uploaded_file = st.file_uploader(
            label="Drag and drop or browse",
            type=["pdf"],
            help=f"PDF only — max {MAX_PDF_SIZE_MB} MB",
            label_visibility="collapsed",
        )

        if uploaded_file:
            size_mb = uploaded_file.size / (1024 * 1024)
            st.markdown(
                f"<div style='display:flex;align-items:center;gap:0.5rem;"
                f"padding:0.55rem 0.9rem;background:rgba(16,185,129,0.08);"
                f"border:1px solid rgba(16,185,129,0.22);border-radius:10px;"
                f"font-size:0.88rem;color:#10b981;margin-top:0.5rem'>"
                f"<span>✅</span>"
                f"<span><strong>{uploaded_file.name}</strong> &nbsp;·&nbsp; {size_mb:.2f} MB</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div style='padding:0.5rem 0;font-size:0.83rem;color:#9ca3af'>"
                "Accepted format: PDF &nbsp;|&nbsp; Max size: 5 MB</div>",
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)

    # ── Right: Job Description ───────────────
    with col_right:
        st.markdown(
            "<div class='card'>"
            "<h3>💼 Job Description</h3>",
            unsafe_allow_html=True,
        )
        job_description = st.text_area(
            label="Job Description",
            placeholder=JD_PLACEHOLDER,
            height=220,
            max_chars=5000,
            label_visibility="collapsed",
        )

        word_count = len(job_description.split()) if job_description.strip() else 0
        color = "#10b981" if word_count >= MIN_JD_WORDS else "#9ca3af"
        st.markdown(
            f"<div style='font-size:0.8rem;color:{color};text-align:right;"
            f"margin-top:0.2rem'>{word_count} words</div>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    return uploaded_file, job_description

# ─────────────────────────────────────────────
# Analyze Button + Validation
# ─────────────────────────────────────────────
def render_analyze_button(uploaded_file, job_description: str) -> bool:
    """
    Renders the Analyze button with live validation feedback.
    Returns True when the button is clicked and inputs are valid.
    """
    st.markdown("<div style='margin: 0.5rem 0 1rem'></div>", unsafe_allow_html=True)

    btn_col, _ = st.columns([1, 2])
    with btn_col:
        clicked = st.button("🔍 Analyze Resume", use_container_width=True)

    if clicked:
        errors = []
        if not uploaded_file:
            errors.append("Please upload a resume PDF.")
        if not job_description.strip():
            errors.append("Please paste a job description.")
        elif len(job_description.split()) < MIN_JD_WORDS:
            errors.append(
                f"Job description is too short — add at least {MIN_JD_WORDS} words."
            )

        if errors:
            for err in errors:
                st.error(f"⚠️  {err}")
            return False
        return True

    return False

# ─────────────────────────────────────────────
# Placeholder Results Section
# ─────────────────────────────────────────────
def _score_color(score: int) -> str:
    if score >= 75:
        return "#10b981"
    if score >= 50:
        return "#f59e0b"
    return "#ef4444"


def render_score_card(ats: ATSResult) -> None:
    """Render the ATS score ring using live ATSResult data."""
    score  = ats["total_score"]
    grade  = ats["grade"]
    status = ats["status"]
    color  = _score_color(score)

    status_bg     = "rgba(16,185,129,0.12)" if status == "PASS" else "rgba(239,68,68,0.12)"
    status_border = "rgba(16,185,129,0.30)" if status == "PASS" else "rgba(239,68,68,0.30)"
    status_color  = "#10b981"               if status == "PASS" else "#ef4444"

    circumference = 2 * 3.14159 * 65
    dash_offset   = circumference * (1 - score / 100)

    st.markdown(
        f"""
        <div class='card' style='text-align:center'>
            <h3 style='text-align:center;justify-content:center'>📊 ATS Compatibility Score</h3>
            <div class='score-ring-wrap'>
                <svg width="160" height="160" viewBox="0 0 160 160">
                    <circle cx="80" cy="80" r="65" fill="none"
                        stroke="rgba(255,255,255,0.04)" stroke-width="12"/>
                    <circle cx="80" cy="80" r="65" fill="none"
                        stroke="{color}" stroke-width="12"
                        stroke-linecap="round"
                        stroke-dasharray="{circumference:.2f}"
                        stroke-dashoffset="{dash_offset:.2f}"
                        transform="rotate(-90 80 80)"/>
                    <text x="80" y="75" text-anchor="middle"
                        font-size="34" font-weight="800" fill="{color}"
                        font-family="'Outfit', sans-serif">{score}</text>
                    <text x="80" y="96" text-anchor="middle"
                        font-size="12" fill="#9ca3af"
                        font-family="'Outfit', sans-serif">out of 100</text>
                </svg>
                <div style='margin-top:0.8rem;font-size:2.2rem;font-weight:800;
                            color:{color};line-height:1;font-family:\'Outfit\',sans-serif'>{grade}</div>
                <div style='margin-top:0.7rem;padding:0.35rem 1.4rem;
                            background:{status_bg};border:1px solid {status_border};
                            border-radius:20px;color:{status_color};
                            font-weight:700;font-size:0.85rem;letter-spacing:0.5px'>{status}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_score_breakdown(ats: ATSResult) -> None:
    """Render four component tiles driven by live ATSResult breakdown."""
    bd = ats["breakdown"]
    st.markdown("<div class='card'><h3>📐 Score Breakdown</h3>", unsafe_allow_html=True)

    components = [
        ("🔑 Keyword Match", bd["keyword_score"],  bd["keyword_max"],  "Keyword overlap with JD"),
        ("🗂️ Coverage",      bd["coverage_score"], bd["coverage_max"], "JD skill categories covered"),
        ("📊 Depth",         bd["depth_score"],    bd["depth_max"],    "Total matched keyword count"),
        ("🤝 Soft Skills",   bd["soft_score"],     bd["soft_max"],     "Soft-skill keyword overlap"),
    ]

    cols = st.columns(4, gap="small")
    for col, (label, score, max_pts, tooltip) in zip(cols, components):
        pct   = (score / max_pts * 100) if max_pts else 0
        color = ("#10b981" if pct >= 70 else
                 "#f59e0b" if pct >= 40 else
                 "#ef4444")
        with col:
            st.markdown(
                f"<div style='text-align:center;padding:0.95rem 0.5rem;"
                f"background:rgba(255,255,255,0.02);border-radius:12px;"
                f"border:1px solid rgba(255,255,255,0.05)' title='{tooltip}'>"
                f"<div style='font-size:0.8rem;color:#9ca3af;margin-bottom:0.4rem'>{label}</div>"
                f"<div style='font-size:1.5rem;font-weight:800;color:{color};font-family:\'Outfit\',sans-serif'>"
                f"{score:.0f}<span style='font-size:0.8rem;color:#6b7280;font-weight:400'>"
                f"/{max_pts}</span></div>"
                f"<div style='margin-top:0.6rem;background:rgba(255,255,255,0.05);"
                f"border-radius:99px;height:5px'>"
                f"<div style='width:{min(pct,100):.1f}%;background:{color};"
                f"border-radius:99px;height:5px;box-shadow:0 0 6px {color}88'></div></div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    # Overall progress bar
    total = ats["total_score"]
    bar_color = _score_color(total)
    st.markdown(
        f"<div style='margin-top:1.2rem'>"
        f"<div style='display:flex;justify-content:space-between;"
        f"font-size:0.82rem;color:#9ca3af;margin-bottom:0.4rem'>"
        f"<span>Overall ATS Score</span>"
        f"<span style='color:{bar_color};font-weight:800;font-family:\'Outfit\',sans-serif'>{total}/100</span></div>"
        f"<div style='background:rgba(255,255,255,0.05);border-radius:99px;height:10px'>"
        f"<div style='width:{total}%;background:linear-gradient(90deg, {bar_color}, {bar_color}CC);"
        f"border-radius:99px;height:10px;box-shadow:0 0 8px {bar_color}AA'></div></div>"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)


def render_keyword_analysis(match: MatchResult, resume_kw: KeywordResult, jd_kw: KeywordResult) -> None:
    """Render live keyword match results from the matcher."""
    st.markdown("<div class='card'><h3>🔑 Keyword Analysis</h3>", unsafe_allow_html=True)

    # ── Match rate bar ───────────────────────────────────────────────────────
    pct = match["match_pct"]
    bar_color = _score_color(int(pct))
    st.markdown(
        f"<div style='margin-bottom:1.2rem'>"
        f"<div style='display:flex;justify-content:space-between;font-size:0.82rem;"
        f"color:#9ca3af;margin-bottom:0.4rem'>"
        f"<span>Keyword Match Rate</span>"
        f"<span style='color:{bar_color};font-weight:800;font-family:\'Outfit\',sans-serif'>{pct:.1f}%</span></div>"
        f"<div style='background:rgba(255,255,255,0.05);border-radius:99px;height:8px'>"
        f"<div style='width:{min(pct,100):.1f}%;background:{bar_color};"
        f"border-radius:99px;height:8px;box-shadow:0 0 6px {bar_color}88;transition:width 0.4s ease'></div>"
        f"</div></div>",
        unsafe_allow_html=True,
    )

    # ── Matched / Missing columns ────────────────────────────────────────────
    k_col1, k_col2 = st.columns(2, gap="medium")

    def _tag_list(keywords: list[str], fg: str, bg: str, border: str) -> str:
        if not keywords:
            return f"<span style='font-size:0.82rem;color:#6b7280;font-style:italic'>None found</span>"
        return "".join(
            f"<span style='display:inline-block;padding:0.25rem 0.75rem;"
            f"background:{bg};border:1px solid {border};"
            f"border-radius:20px;font-size:0.8rem;color:{fg};margin:0.2rem;font-weight:500'>{kw}</span>"
            for kw in keywords
        )

    with k_col1:
        st.markdown(
            f"<div style='font-size:0.88rem;font-weight:700;color:#10b981;margin-bottom:0.6rem'>"
            f"✅ Matched  <span style='font-weight:400;color:#6b7280'>({len(match['matched'])})</span></div>"
            f"<div style='line-height:2.2'>"
            f"{_tag_list(match['matched'], '#10b981', 'rgba(16,185,129,0.08)', 'rgba(16,185,129,0.22)')}"
            f"</div>",
            unsafe_allow_html=True,
        )

    with k_col2:
        st.markdown(
            f"<div style='font-size:0.88rem;font-weight:700;color:#ef4444;margin-bottom:0.6rem'>"
            f"❌ Missing  <span style='font-weight:400;color:#6b7280'>({len(match['missing'])})</span></div>"
            f"<div style='line-height:2.2'>"
            f"{_tag_list(match['missing'], '#ef4444', 'rgba(239,68,68,0.08)', 'rgba(239,68,68,0.22)')}"
            f"</div>",
            unsafe_allow_html=True,
        )

    # ── Extra keywords (bonus) ────────────────────────────────────────────
    if match["extra"]:
        st.markdown(
            f"<div style='margin-top:1rem;padding-top:0.8rem;"
            f"border-top:1px solid rgba(255,255,255,0.05)'>"
            f"<div style='font-size:0.85rem;font-weight:700;color:#38bdf8;margin-bottom:0.5rem'>"
            f"💡 Bonus skills on your resume not required by this JD "
            f"<span style='font-weight:400;color:#6b7280'>({len(match['extra'])})</span></div>"
            f"<div style='line-height:2.2'>"
            f"{_tag_list(match['extra'], '#38bdf8', 'rgba(56,189,248,0.08)', 'rgba(56,189,248,0.22)')}"
            f"</div></div>",
            unsafe_allow_html=True,
        )

    # ── Per-category breakdown ────────────────────────────────────────────
    with st.expander("📂 View keywords by category", expanded=False):
        all_cats = sorted(
            set(resume_kw["by_category"]) | set(jd_kw["by_category"])
        )
        if not all_cats:
            st.markdown("<span style='color:#6b7280;font-size:0.85rem'>No categorised keywords found.</span>",
                        unsafe_allow_html=True)
        for cat in all_cats:
            r_set = set(resume_kw["by_category"].get(cat, []))
            j_set = set(jd_kw["by_category"].get(cat, []))
            all_in_cat = sorted(r_set | j_set)
            tags = ""
            for kw in all_in_cat:
                in_resume = kw in r_set
                in_jd     = kw in j_set
                if in_resume and in_jd:
                    fg, bg, bd = "#10b981", "rgba(16,185,129,0.08)", "rgba(16,185,129,0.22)"
                elif in_jd:
                    fg, bg, bd = "#ef4444", "rgba(239,68,68,0.08)", "rgba(239,68,68,0.22)"
                else:
                    fg, bg, bd = "#38bdf8", "rgba(56,189,248,0.06)", "rgba(56,189,248,0.18)"
                tags += (
                    f"<span style='display:inline-block;padding:0.2rem 0.65rem;"
                    f"background:{bg};border:1px solid {bd};border-radius:20px;"
                    f"font-size:0.78rem;color:{fg};margin:0.18rem;font-weight:500'>{kw}</span>"
                )
            st.markdown(
                f"<div style='margin-bottom:0.7rem'>"
                f"<div style='font-size:0.82rem;font-weight:700;color:#c084fc;"
                f"margin-bottom:0.35rem'>{cat}</div>"
                f"<div style='line-height:2.1'>{tags}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.markdown("</div>", unsafe_allow_html=True)



def render_ai_report(report: LLMReport) -> None:
    """Render the full LLM report — nine sections in a styled card."""

    # ── Section display config ──────────────────────────────────────────────
    SECTION_META: dict[str, tuple[str, str]] = {
        "Overall Resume Review":      ("🧠", "#a78bfa"),
        "Strengths":                  ("💪", "#2ecc71"),
        "Weaknesses":                 ("⚠️",  "#f39c12"),
        "Missing Technical Skills":   ("❌", "#e74c3c"),
        "Suggestions for Improvement":("💡", "#60a5fa"),
        "Resume Summary":             ("📝", "#c084fc"),
        "Career Advice":              ("🚀", "#34d399"),
        "Improved Bullet Points":     ("✍️", "#f43f5e"),
        "Interview Questions":        ("❓", "#fbbf24"),
    }

    # ── Meta bar: model · inference time ───────────────────────────────────
    st.markdown(
        f"<div style='display:flex;gap:1.2rem;font-size:0.78rem;color:#64748b;"
        f"margin-bottom:1rem;flex-wrap:wrap'>"
        f"<span>🦙 Model: <strong style='color:#c4b5fd'>{report['model']}</strong></span>"
        f"<span>⏱ Generated in <strong style='color:#c4b5fd'>{report['duration_s']:.1f}s</strong></span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    sections = report["sections"]

    # ── Rows 1 & 2: three sections side-by-side ────────────────────────────
    row1 = ["Overall Resume Review", "Strengths", "Weaknesses"]
    cols = st.columns(3, gap="medium")
    for col, key in zip(cols, row1):
        icon, accent = SECTION_META[key]
        content = sections.get(key, "")
        with col:
            st.markdown(
                f"<div class='card' style='min-height:220px'>"
                f"<h3>{icon} {key}</h3>",
                unsafe_allow_html=True,
            )
            if content:
                st.markdown(content)
            else:
                st.markdown(
                    "<span style='color:#64748b;font-size:0.85rem;font-style:italic'>"
                    "No content returned.</span>",
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)

    # ── Row 3: Missing Skills (full width) ────────────────────────────────
    key = "Missing Technical Skills"
    icon, accent = SECTION_META[key]
    st.markdown(
        f"<div class='card'><h3>{icon} {key}</h3>",
        unsafe_allow_html=True,
    )
    content = sections.get(key, "")
    if content:
        st.markdown(content)
    else:
        st.markdown(
            "<span style='color:#64748b;font-size:0.85rem;font-style:italic'>"
            "No missing skills identified.</span>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Row 4: Suggestions + Resume Summary ──────────────────────────────
    r4_left, r4_right = st.columns([3, 2], gap="large")
    for col, key in [(r4_left, "Suggestions for Improvement"),
                     (r4_right, "Resume Summary")]:
        icon, accent = SECTION_META[key]
        content = sections.get(key, "")
        with col:
            st.markdown(
                f"<div class='card'><h3>{icon} {key}</h3>",
                unsafe_allow_html=True,
            )
            if content:
                st.markdown(content)
            else:
                st.markdown(
                    "<span style='color:#64748b;font-size:0.85rem;font-style:italic'>"
                    "No content returned.</span>",
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)

    # ── Row 5: Improved Bullet Points + Interview Questions ───────────────
    r5_left, r5_right = st.columns(2, gap="large")
    for col, key in [(r5_left, "Improved Bullet Points"),
                     (r5_right, "Interview Questions")]:
        icon, accent = SECTION_META[key]
        content = sections.get(key, "")
        with col:
            st.markdown(
                f"<div class='card'><h3>{icon} {key}</h3>",
                unsafe_allow_html=True,
            )
            if content:
                st.markdown(content)
            else:
                st.markdown(
                    "<span style='color:#64748b;font-size:0.85rem;font-style:italic'>"
                    "No content returned.</span>",
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)

    # ── Row 6: Career Advice (full width) ────────────────────────────────
    key = "Career Advice"
    icon, accent = SECTION_META[key]
    st.markdown(
        f"<div class='card'><h3>{icon} {key}</h3>",
        unsafe_allow_html=True,
    )
    content = sections.get(key, "")
    if content:
        st.markdown(content)
    else:
        st.markdown(
            "<span style='color:#64748b;font-size:0.85rem;font-style:italic'>"
            "No content returned.</span>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Raw output expander (debug) ───────────────────────────────────────
    with st.expander("🔍 View raw LLM output", expanded=False):
        st.code(report["raw_markdown"], language="markdown")


def render_resume_preview(parsed: ParseResult) -> None:
    """Display extracted resume text and parser metadata."""
    st.markdown(
        "<div class='card'><h3>📄 Extracted Resume Text</h3>",
        unsafe_allow_html=True,
    )

    # ── Meta bar: pages · words · engine ────────────────────────────────────
    engine_color = "#10b981" if parsed["engine"] == "pdfplumber" else "#f59e0b"
    st.markdown(
        f"<div style='display:flex;gap:1.2rem;font-size:0.8rem;color:#9ca3af;"
        f"margin-bottom:0.8rem;flex-wrap:wrap'>"
        f"<span>📄 <strong style='color:#c084fc'>{parsed['page_count']}</strong> page(s)</span>"
        f"<span>🔤 <strong style='color:#c084fc'>{parsed['word_count']:,}</strong> words</span>"
        f"<span>⚙️ Engine: <strong style='color:{engine_color}'>{parsed['engine']}</strong></span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── Scrollable text box ──────────────────────────────────────────────────
    import html as html_mod
    safe_text = html_mod.escape(parsed["text"])
    safe_text = safe_text.replace("\n", "<br>")

    st.markdown(
        f"<div class='preview-box'>"
        f"{safe_text}"
        f"</div>",
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)


def render_skill_recommendations(recs: SkillRecommendations) -> None:
    """Render four recommendation panels: technologies, frameworks, certs, projects."""
    st.markdown("<div class='card'><h3>🎓 Skill Recommendations</h3>", unsafe_allow_html=True)

    has_any = any([
        recs["technologies"], recs["frameworks"],
        recs["certifications"], recs["projects"],
    ])
    if not has_any:
        st.markdown(
            "<p style='color:#6b7280;font-size:0.95rem;font-style:italic'>No specific recommendations — "
            "your resume already covers the key skills in this JD.</p>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
        return

    priority_pill = {
        "High":   ("🔴", "#ef4444", "rgba(239,68,68,0.08)",  "rgba(239,68,68,0.25)"),
        "Medium": ("🟡", "#f59e0b", "rgba(245,158,11,0.08)", "rgba(245,158,11,0.25)"),
        "Low":    ("🟢", "#10b981", "rgba(16,185,129,0.08)", "rgba(16,185,129,0.25)"),
    }

    def _rec_item(rec: dict) -> str:
        emoji, fc, bg, bd = priority_pill.get(rec["priority"], ("⚪","#9ca3af","rgba(255,255,255,0.03)","rgba(255,255,255,0.08)"))
        return (
            f"<div style='padding:0.8rem 1rem;background:{bg};"
            f"border:1px solid {bd};border-radius:10px;margin-bottom:0.6rem'>"
            f"<div style='display:flex;align-items:center;gap:0.5rem;margin-bottom:0.3rem'>"
            f"<span style='font-size:0.75rem;font-weight:700;color:{fc};"
            f"background:rgba(0,0,0,0.25);padding:0.15rem 0.5rem;border-radius:4px;letter-spacing:0.5px'>"
            f"{rec['priority'].upper()}</span>"
            f"<strong style='font-size:0.92rem;color:#f3f4f6'>{rec['name']}</strong></div>"
            f"<div style='font-size:0.82rem;color:#9ca3af;line-height:1.55'>{rec['reason']}</div>"
            f"</div>"
        )

    panels = [
        ("⚙️ Technologies to Learn",   recs["technologies"]),
        ("🧩 Frameworks to Learn",     recs["frameworks"]),
        ("📜 Certifications",          recs["certifications"]),
        ("🔨 Project Ideas",           recs["projects"]),
    ]

    # Render non-empty panels in a 2-column grid
    non_empty = [(title, items) for title, items in panels if items]
    rows = [non_empty[i:i+2] for i in range(0, len(non_empty), 2)]

    for row in rows:
        cols = st.columns(len(row), gap="medium")
        for col, (title, items) in zip(cols, row):
            with col:
                st.markdown(
                    f"<div style='font-size:0.9rem;font-weight:700;color:#c084fc;"
                    f"margin-bottom:0.6rem;margin-top:0.4rem'>{title}</div>",
                    unsafe_allow_html=True,
                )
                st.markdown("".join(_rec_item(r) for r in items), unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


def render_section_analysis(analysis: SectionAnalysis) -> None:
    """Render resume section completeness with Present / Missing / Needs Improvement."""
    st.markdown("<div class='card'><h3>🗂️ Resume Section Analysis</h3>", unsafe_allow_html=True)

    # ── Completeness score bar ────────────────────────────────────────────
    score = analysis["score"]
    bar_color = (
        "#10b981" if score >= 75 else
        "#f59e0b" if score >= 50 else
        "#ef4444"
    )
    st.markdown(
        f"<div style='margin-bottom:1.2rem'>"
        f"<div style='display:flex;justify-content:space-between;"
        f"font-size:0.82rem;color:#9ca3af;margin-bottom:0.4rem'>"
        f"<span>Resume Completeness</span>"
        f"<span style='color:{bar_color};font-weight:800;font-family:\'Outfit\',sans-serif'>{score}/100</span></div>"
        f"<div style='background:rgba(255,255,255,0.05);border-radius:99px;height:9px'>"
        f"<div style='width:{score}%;background:linear-gradient(90deg, {bar_color}, {bar_color}CC);"
        f"border-radius:99px;height:9px;box-shadow:0 0 6px {bar_color}88'></div></div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── Legend ────────────────────────────────────────────────────────────
    st.markdown(
        "<div style='display:flex;gap:1.2rem;font-size:0.8rem;"
        "color:#9ca3af;margin-bottom:1rem;flex-wrap:wrap'>"
        "<span><strong style='color:#10b981'>●</strong> Present</span>"
        "<span><strong style='color:#f59e0b'>●</strong> Needs Improvement</span>"
        "<span><strong style='color:#ef4444'>●</strong> Missing</span>"
        "</div>",
        unsafe_allow_html=True,
    )

    # ── Section tiles ─────────────────────────────────────────────────────
    STATUS_STYLE = {
        "present": {
            "dot": "#10b981",
            "bg":  "rgba(16,185,129,0.06)",
            "bd":  "rgba(16,185,129,0.22)",
            "label": "Present",
            "label_color": "#10b981",
            "icon": "✅",
        },
        "needs_improvement": {
            "dot": "#f59e0b",
            "bg":  "rgba(245,158,11,0.06)",
            "bd":  "rgba(245,158,11,0.22)",
            "label": "Needs Improvement",
            "label_color": "#f59e0b",
            "icon": "⚠️",
        },
        "missing": {
            "dot": "#ef4444",
            "bg":  "rgba(239,68,68,0.06)",
            "bd":  "rgba(239,68,68,0.22)",
            "label": "Missing",
            "label_color": "#ef4444",
            "icon": "❌",
        },
    }

    section_names = list(analysis["sections"].keys())
    # 4-column grid
    rows = [section_names[i:i+4] for i in range(0, len(section_names), 4)]

    for row in rows:
        cols = st.columns(len(row), gap="small")
        for col, name in zip(cols, row):
            info   = analysis["sections"][name]
            style  = STATUS_STYLE[info["status"]]
            wc_str = f"{info['word_count']} words" if info["word_count"] else ""
            wc_html = (
                "<div style='font-size:0.75rem;color:#9ca3af;margin-top:0.25rem'>"
                + wc_str + "</div>"
            ) if wc_str else ""
            with col:
                st.markdown(
                    f"<div style='text-align:center;padding:0.95rem 0.5rem;"
                    f"background:{style['bg']};border:1px solid {style['bd']};"
                    f"border-radius:12px;min-height:115px'>"
                    f"<div style='font-size:1.4rem'>{style['icon']}</div>"
                    f"<div style='font-size:0.85rem;font-weight:600;color:#e2e8f0;"
                    f"margin:0.3rem 0 0.15rem'>{name}</div>"
                    f"<div style='font-size:0.72rem;font-weight:600;"
                    f"color:{style['label_color']}'>{style['label']}</div>"
                    f"{wc_html}"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    # ── Recommendations for missing / weak ────────────────────────────────
    flagged = analysis["missing"] + analysis["weak"]
    if flagged:
        st.markdown(
            "<div style='margin-top:1rem;padding-top:0.9rem;"
            "border-top:1px solid rgba(255,255,255,0.07)'>"
            "<div style='font-size:0.85rem;font-weight:600;color:#a78bfa;"
            "margin-bottom:0.6rem'>💡 Recommendations</div>",
            unsafe_allow_html=True,
        )
        for name in flagged:
            info  = analysis["sections"][name]
            rec   = info["recommendation"]
            color = "#e74c3c" if info["status"] == "missing" else "#f39c12"
            if rec:
                st.markdown(
                    f"<div style='display:flex;gap:0.7rem;align-items:flex-start;"
                    f"padding:0.5rem 0;border-bottom:1px solid rgba(255,255,255,0.04)'>"
                    f"<span style='font-size:0.78rem;font-weight:700;color:{color};"
                    f"white-space:nowrap;padding-top:0.1rem'>{name}</span>"
                    f"<span style='font-size:0.82rem;color:#94a3b8;line-height:1.5'>{rec}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


def render_results(
    parsed: ParseResult,
    ats: ATSResult,
    match: MatchResult,
    resume_kw: KeywordResult,
    jd_kw: KeywordResult,
    report: LLMReport,
    recs: SkillRecommendations,
    section_analysis: SectionAnalysis,
) -> None:
    """Orchestrates the full results area."""
    st.markdown(
        "<hr style='border:none;border-top:1px solid rgba(255,255,255,0.08);"
        "margin:1.5rem 0 1.8rem'>",
        unsafe_allow_html=True,
    )

    # ── PDF generation & Download button ───────────────────────────────────────
    pdf_bytes = generate_pdf_report(
        parsed=parsed,
        ats=ats,
        match=match,
        resume_kw=resume_kw,
        jd_kw=jd_kw,
        report=report,
        recs=recs,
        section_analysis=section_analysis,
        filename="ATS_Evaluation_Report.pdf"
    )

    title_col, btn_col = st.columns([3, 1])
    with title_col:
        st.markdown(
            "<div style='font-size:1.35rem;font-weight:700;color:#e2e8f0;"
            "margin-top:0.4rem'>📈 Analysis Report</div>",
            unsafe_allow_html=True,
        )
    with btn_col:
        st.download_button(
            label="📥 Download PDF Report",
            data=pdf_bytes,
            file_name="ATS_Evaluation_Report.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    # Row 1: Score ring (left) + breakdown + resume preview (right)
    r1_left, r1_right = st.columns([1, 2], gap="large")
    with r1_left:
        render_score_card(ats)
    with r1_right:
        render_score_breakdown(ats)
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
        render_resume_preview(parsed)

    # Row 2: Section analysis + Keyword analysis side by side
    r2_left, r2_right = st.columns([1, 1], gap="large")
    with r2_left:
        render_section_analysis(section_analysis)
    with r2_right:
        render_keyword_analysis(match, resume_kw, jd_kw)

    # Row 3: Skill recommendations (full width)
    render_skill_recommendations(recs)

    # Row 4+: AI report (live LLM output)
    st.markdown(
        "<div style='font-size:1.1rem;font-weight:700;color:#e2e8f0;"
        "margin:1rem 0 0.8rem'>🤖 AI-Powered Analysis</div>",
        unsafe_allow_html=True,
    )
    if not report["success"]:
        st.error(
            f"⚠️  AI analysis unavailable — {report['error']}\n\n"
            "The ATS score and keyword results above are still accurate."
        )
    else:
        render_ai_report(report)


# ─────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────
def render_footer() -> None:
    st.markdown(
        f"""
        <div style='
            margin-top: 3rem;
            padding: 1.4rem 0 1rem;
            border-top: 1px solid rgba(255,255,255,0.08);
            text-align: center;
        '>
            <div style='
                font-size: 0.82rem;
                color: #475569;
                letter-spacing: 0.3px;
                line-height: 2;
            '>
                {APP_ICON} <strong style='color:#7c6aab'>{APP_TITLE}</strong>
                &nbsp;·&nbsp;
                Built with Python, Streamlit &amp; Llama3
                &nbsp;·&nbsp;
                Runs 100% locally
            </div>
            <div style='
                margin-top: 0.35rem;
                font-size: 0.8rem;
                background: linear-gradient(90deg, #a78bfa, #60a5fa);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                font-weight: 600;
                letter-spacing: 0.4px;
            '>
                Made by {AUTHOR}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────
def main() -> None:
    inject_css()
    render_sidebar()
    render_header()

    uploaded_file, job_description = render_inputs()
    analyze_clicked = render_analyze_button(uploaded_file, job_description)

    if analyze_clicked:
        # ── Step 1: parse resume PDF ─────────────────────────────────────
        with st.spinner("📄 Extracting resume text…"):
            parsed = parse_resume(uploaded_file)

        if not parsed["success"]:
            st.error(f"⚠️  Could not parse your resume — {parsed['error']}")
            render_footer()
            return

        # ── Step 2: parse job description ────────────────────────────────
        with st.spinner("💼 Processing job description…"):
            jd_result = parse_job_description(job_description)

        if not jd_result["success"]:
            st.error(f"⚠️  Job description issue — {jd_result['error']}")
            render_footer()
            return

        # ── Step 3: extract keywords from both ───────────────────────────
        with st.spinner("🔑 Extracting keywords…"):
            resume_kw = extract_keywords(parsed["text"])
            jd_kw     = extract_keywords(jd_result["text"])
            match     = match_keywords(resume_kw, jd_kw)

        # ── Step 4: calculate ATS score ───────────────────────────────────
        with st.spinner("📊 Calculating ATS score…"):
            ats = calculate_ats_score(match, resume_kw, jd_kw)

        # ── Step 5: skill recommendations + section analysis ─────────────
        with st.spinner("🗂️ Analysing resume sections & generating recommendations…"):
            recs             = recommend_skills(match["missing"], jd_kw)
            section_analysis = analyze_sections(parsed["text"])

        # ── Step 6: LLM analysis ──────────────────────────────────────────
        with st.spinner("🦙 Running AI analysis — this may take 20-40 seconds…"):
            ctx: PromptContext = {
                "resume_text":    parsed["text"],
                "jd_text":        jd_result["text"],
                "matched_skills": match["matched"],
                "missing_skills": match["missing"],
                "ats_score":      ats["total_score"],
                "grade":          ats["grade"],
                "match_pct":      ats["match_pct"],
            }
            report = llm_analyze(ctx)

        # ── Step 7: render results ────────────────────────────────────────
        render_results(parsed, ats, match, resume_kw, jd_kw, report, recs, section_analysis)

    render_footer()


if __name__ == "__main__":
    main()
