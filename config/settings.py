# ============================================================
# config/settings.py
# Centralized configuration constants for the application
# ============================================================

# ---------------------------
# App Metadata
# ---------------------------
APP_TITLE = "AI Resume Optimizer & ATS Analyzer"
APP_SUBTITLE = "Get your resume past the bots — and in front of humans."
APP_ICON = "🎯"
AUTHOR = "Gufran"

# ---------------------------
# Ollama / LLM Configuration
# ---------------------------
OLLAMA_MODEL = "llama3"
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_TIMEOUT = 60  # seconds

# ---------------------------
# ATS Scoring — component maximums (must sum to 100)
# ---------------------------
ATS_MAX_KEYWORD   = 55   # keyword overlap contribution
ATS_MAX_COVERAGE  = 15   # breadth: JD skill categories covered
ATS_MAX_DEPTH     = 15   # depth: total matched keyword count
ATS_MAX_SOFT      = 15   # soft-skill keyword overlap

# ---------------------------
# Score Thresholds
# ---------------------------
PASSING_ATS_SCORE = 70

# ---------------------------
# Grade bands  { min_score: label }
# ---------------------------
SCORE_GRADE_BANDS: list[tuple[int, str]] = [
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

# ---------------------------
# Score Color Bands (for UI)
# ---------------------------
SCORE_COLOR_HIGH   = "#2ecc71"   # green  — 75 and above
SCORE_COLOR_MEDIUM = "#f39c12"   # orange — 50–74
SCORE_COLOR_LOW    = "#e74c3c"   # red    — below 50

# ---------------------------
# Resume Section Headers
# (used for section detection)
# ---------------------------
EDUCATION_HEADERS    = ["education", "academic background", "qualifications", "academic history"]
EXPERIENCE_HEADERS   = ["experience", "work experience", "employment", "work history", "professional experience"]
SKILLS_HEADERS       = ["skills", "technical skills", "competencies", "core competencies", "key skills"]
SUMMARY_HEADERS      = ["summary", "professional summary", "profile", "objective", "about me"]
PROJECTS_HEADERS     = ["projects", "personal projects", "academic projects", "portfolio"]
CERTIFICATIONS_HEADERS = ["certifications", "certificates", "licenses", "accreditations"]

# ---------------------------
# UI Layout
# ---------------------------
MAX_JD_CHARS         = 5000   # character cap for job description input
MIN_JD_WORDS         = 30     # minimum words required to run analysis
MAX_PDF_SIZE_MB      = 5      # maximum allowed PDF file size

# ---------------------------
# Placeholder / Demo Text
# ---------------------------
JD_PLACEHOLDER = """Paste the full job description here.

Example:
We are looking for a Python Developer with strong experience in
FastAPI, Docker, and PostgreSQL. The ideal candidate will have 2+
years of backend development experience, familiarity with RESTful
APIs, and excellent problem-solving skills. Knowledge of AWS or GCP
is a plus."""

# ---------------------------
# Tech Stack (shown in sidebar)
# ---------------------------
TECH_STACK = [
    ("🐍", "Python 3.9+"),
    ("🌐", "Streamlit"),
    ("🦙", "Ollama + Llama3"),
    ("📄", "pdfplumber / PyPDF2"),
    ("🐼", "pandas"),
]

# ---------------------------
# Sidebar Description
# ---------------------------
SIDEBAR_DESCRIPTION = (
    "Upload your resume and paste a job description. "
    "The AI engine will score your resume against ATS systems, "
    "identify missing keywords, and generate targeted suggestions "
    "to improve your chances of landing an interview."
)
