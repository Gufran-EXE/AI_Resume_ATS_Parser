# AI-Powered Resume Optimizer & Local ATS Analyzer 🚀

A comprehensive, private, and local Resume optimizer and applicant tracking system (ATS) parser. This application parses resume PDF files, compares them against a target Job Description (JD), scores them across critical keyword and category metrics, and uses a local Large Language Model (LLM) to generate detailed, structured improvements, XYZ-formatted bullet points, and customized interview preparation questions.

All parsing, matching, and generation run 100% locally on your machine—ensuring complete privacy for personal information.

---

## ✨ Features

- **Local LLM Analysis:** Uses **Ollama + Llama3** to perform resume audits, weakness identification, formatting optimization, and improvement generation.
- **ATS Compatibility Scoring:** Computes detailed match percentages, component breakdowns (Keyword Match, Skill Coverage, Keyword Depth, Soft Skills), grades, and pass/fail statuses.
- **Resume Section Completeness Audit:** Analyzes key parts of a resume (Experience, Skills, Education, Projects, Summary, Certifications) and checks for presence, formatting strength, and word count.
- **Keyword & Skill Analysis:** Categorizes keywords automatically and checks for matched, missing, and extra "bonus" skills.
- **Downloadable PDF Report:** Generates a highly polished, stylized PDF report using **ReportLab** containing full metadata, score layouts, section metrics, and custom suggestions.
- **Sleek UI/UX:** A modernized dark-glass Streamlit theme featuring fluid metrics, card components, glowing progress trackers, hover transitions, and responsive sidebars.

---

## 🛠️ Tech Stack

- **Frontend:** Streamlit
- **PDF Engine:** ReportLab
- **Parsing:** PyPDF2 / pdfplumber
- **Local AI:** Ollama (Llama3 Model)
- **Programming Language:** Python 3.9+

---

## 🚀 Getting Started

### 1. Prerequisites

- Make sure you have Python installed (version 3.9 or higher).
- Install [Ollama](https://ollama.com/) on your local machine.

### 2. Clone the Repository

```bash
git clone https://github.com/Gufran-EXE/AI_Resume_ATS_Parser.git
cd AI_Resume_ATS_Parser
```

### 3. Install Dependencies

Install required libraries using the package manager:

```bash
pip install -r requirements.txt
```

### 4. Start the Local LLM Server

Start the local Ollama instance:

```bash
ollama serve
```

In another terminal, download the Llama3 model required by the analyzer:

```bash
ollama pull llama3
```

### 5. Run the Application

Launch the Streamlit dashboard:

```bash
streamlit run app.py
```

The web portal will automatically open in your default browser at `http://localhost:8501`.

---

## 📁 Project Structure

```text
├── app.py                     # Main Streamlit web application & UI renderer
├── requirements.txt           # Python library dependencies
├── PROJECT_SPEC.md            # Detailed application specification sheet
├── config/
│   └── settings.py            # Global variables, score boundaries, and thresholds
└── modules/
    ├── ats_scoring.py         # ATS scoring algorithms & grade weights
    ├── job_description_parser.py # Keyword extractor for Job Descriptions
    ├── keyword_matcher.py     # Categorizer & overlap matcher for resume vs. JD keywords
    ├── llm_analyzer.py        # Local Ollama client & prompt generator
    ├── pdf_generator.py       # ReportLab PDF compiler & NumberedCanvas settings
    ├── prompts.py             # Prompt templates and formatting guidelines for Llama3
    ├── resume_parser.py       # PDF parser & text extractor for resume files
    ├── section_analyzer.py    # Section finder & word count validator
    ├── skill_recommender.py   # Rule-based suggestions engine (Frameworks, Projects, Certs)
    └── utils.py               # Shared utility functions
```

---

## 🔒 Privacy & Security

This application respects your privacy:
- **No Remote API Calls:** No external cloud services are contacted during analysis.
- **Local Sandbox:** Resumes are parsed, analyzed, and rewritten entirely on your physical machine.
- **Zero Data Retention:** No logs or personal details are uploaded online.

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.
