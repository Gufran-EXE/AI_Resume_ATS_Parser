# AI Resume Optimizer & ATS Analyzer - Project Specification

## 1. Project Overview

**Purpose**: A portfolio-grade application that analyzes resumes against job descriptions using AI, providing ATS compatibility scores, keyword matching, and improvement suggestions.

**Target Audience**: Students, job seekers, career counselors

**Complexity Level**: Clean, modular student portfolio project (not enterprise-level)

---

## 2. Tech Stack

### Core Technologies
- **Python 3.9+**: Primary language
- **Streamlit**: Web interface and UI
- **Ollama + Llama3**: Local LLM for AI analysis
- **pdfplumber**: PDF text extraction (primary)
- **PyPDF2**: Fallback PDF processing
- **pandas**: Data manipulation and reporting

### Additional Libraries
- **re**: Regular expressions for keyword extraction
- **json**: Configuration and data handling
- **typing**: Type hints for code clarity

---

## 3. Project Architecture

```
AI_ATS_Parser/
│
├── app.py                      # Main Streamlit application (UI only)
├── requirements.txt            # Python dependencies
├── README.md                   # Project documentation
├── .gitignore                  # Git ignore rules
│
├── config/
│   └── settings.py             # Configuration constants
│
├── modules/
│   ├── __init__.py
│   ├── resume_parser.py        # PDF extraction & text processing
│   ├── job_description_parser.py  # JD text processing
│   ├── keyword_matcher.py      # Keyword extraction & matching logic
│   ├── ats_scoring.py          # ATS score calculation
│   ├── llm_analyzer.py         # Ollama/Llama3 integration
│   ├── report_generator.py     # Final report compilation
│   └── utils.py                # Helper functions
│
├── data/
│   └── sample_resumes/         # Optional: Sample PDFs for testing
│
└── tests/                      # Optional: Unit tests
    └── test_modules.py
```

---

## 4. Module Specifications

### 4.1 `app.py` - Main Application
**Responsibility**: Streamlit UI orchestration

**Functions**:
- `main()`: Entry point
- `render_header()`: Display app title and instructions
- `upload_resume_section()`: File uploader widget
- `job_description_section()`: Text area for JD input
- `analyze_button_handler()`: Trigger analysis workflow
- `display_results()`: Render ATS report and recommendations

**Workflow**:
1. Display UI components
2. Accept user inputs (resume PDF + JD text)
3. Validate inputs
4. Call analysis pipeline
5. Display results in organized sections

---

### 4.2 `modules/resume_parser.py`
**Responsibility**: Extract and structure text from PDF resumes

**Key Functions**:
```python
def extract_text_from_pdf(file) -> str
    # Primary extraction using pdfplumber
    # Fallback to PyPDF2 if needed
    
def parse_resume_sections(text: str) -> dict
    # Identify sections: contact, education, experience, skills
    # Return structured dictionary
    
def extract_contact_info(text: str) -> dict
    # Extract email, phone, LinkedIn, etc.
    
def extract_skills_section(text: str) -> list
    # Identify and extract skills
```

**Output Format**:
```python
{
    "raw_text": "full text...",
    "sections": {
        "contact": {...},
        "education": "...",
        "experience": "...",
        "skills": [...]
    }
}
```

---

### 4.3 `modules/job_description_parser.py`
**Responsibility**: Process and structure job description text

**Key Functions**:
```python
def parse_job_description(text: str) -> dict
    # Extract key information from JD
    
def extract_required_skills(text: str) -> list
    # Identify must-have skills
    
def extract_preferred_skills(text: str) -> list
    # Identify nice-to-have skills
    
def extract_responsibilities(text: str) -> list
    # Extract key responsibilities
```

**Output Format**:
```python
{
    "raw_text": "...",
    "required_skills": [...],
    "preferred_skills": [...],
    "responsibilities": [...],
    "experience_required": "...",
    "education_required": "..."
}
```

---

### 4.4 `modules/keyword_matcher.py`
**Responsibility**: Compare resume keywords with JD requirements

**Key Functions**:
```python
def extract_keywords(text: str, category: str) -> set
    # Extract keywords using NLP techniques
    # Categories: technical, soft_skills, tools, etc.
    
def calculate_keyword_match(resume_keywords: set, jd_keywords: set) -> dict
    # Calculate match percentage
    # Identify matched, missing, and extra keywords
    
def get_keyword_frequency(text: str, keywords: list) -> dict
    # Count keyword occurrences
```

**Output Format**:
```python
{
    "match_percentage": 75.5,
    "matched_keywords": [...],
    "missing_keywords": [...],
    "extra_keywords": [...],
    "keyword_density": {...}
}
```

---

### 4.5 `modules/ats_scoring.py`
**Responsibility**: Calculate ATS compatibility score

**Scoring Components** (Total: 100 points):
1. **Keyword Match (40 points)**
   - Required skills present
   - Preferred skills present
   
2. **Format Quality (20 points)**
   - Clear section headers
   - Proper structure
   - No complex formatting
   
3. **Content Completeness (20 points)**
   - Contact information
   - Education section
   - Experience section
   - Skills section
   
4. **Relevance (20 points)**
   - Experience alignment
   - Skill relevance
   - Education match

**Key Functions**:
```python
def calculate_ats_score(resume_data: dict, jd_data: dict, keywords: dict) -> dict
    # Main scoring function
    
def score_keyword_match(keywords: dict) -> float
def score_format_quality(resume_data: dict) -> float
def score_content_completeness(resume_data: dict) -> float
def score_relevance(resume_data: dict, jd_data: dict) -> float
```

**Output Format**:
```python
{
    "total_score": 78.5,
    "breakdown": {
        "keyword_match": 35,
        "format_quality": 18,
        "content_completeness": 15,
        "relevance": 10.5
    },
    "grade": "B+",
    "pass_ats": True
}
```

---

### 4.6 `modules/llm_analyzer.py`
**Responsibility**: Use Llama3 via Ollama for intelligent analysis

**Key Functions**:
```python
def initialize_ollama_client() -> object
    # Setup Ollama connection
    
def generate_improvement_suggestions(resume_text: str, jd_text: str) -> list
    # AI-powered suggestions for resume improvement
    
def analyze_experience_relevance(resume_exp: str, jd_resp: str) -> str
    # Analyze how well experience matches requirements
    
def suggest_missing_skills(matched_keywords: dict) -> list
    # Suggest how to acquire/highlight missing skills
    
def rewrite_bullet_points(original: str, jd_context: str) -> str
    # Suggest improved bullet point wording
```

**Prompt Engineering Strategy**:
- Clear, specific prompts
- Provide context (resume + JD snippets)
- Request structured output
- Use few-shot examples if needed

**Output Format**:
```python
{
    "suggestions": [
        {
            "category": "Skills",
            "priority": "High",
            "suggestion": "Add 'Docker' to your skills section..."
        },
        ...
    ],
    "experience_analysis": "Your experience in...",
    "rewritten_bullets": [...]
}
```

---

### 4.7 `modules/report_generator.py`
**Responsibility**: Compile all analysis into a cohesive report

**Key Functions**:
```python
def generate_full_report(resume_data, jd_data, keywords, ats_score, llm_insights) -> dict
    # Combine all analysis components
    
def format_summary_section(data: dict) -> str
    # Executive summary
    
def format_keyword_section(keywords: dict) -> str
    # Keyword analysis display
    
def format_suggestions_section(suggestions: list) -> str
    # AI recommendations
    
def export_report_as_json(report: dict, filename: str)
    # Optional: Save report
```

**Report Structure**:
```python
{
    "summary": {
        "ats_score": 78.5,
        "status": "Pass",
        "grade": "B+",
        "key_strengths": [...],
        "critical_gaps": [...]
    },
    "keyword_analysis": {...},
    "ats_score_breakdown": {...},
    "ai_suggestions": [...],
    "action_items": [...]
}
```

---

### 4.8 `modules/utils.py`
**Responsibility**: Shared utility functions

**Key Functions**:
```python
def clean_text(text: str) -> str
    # Remove special characters, normalize whitespace
    
def tokenize_text(text: str) -> list
    # Split text into tokens
    
def calculate_text_similarity(text1: str, text2: str) -> float
    # Simple similarity metric
    
def validate_pdf(file) -> bool
    # Check if uploaded file is valid PDF
    
def validate_job_description(text: str) -> bool
    # Ensure JD has minimum content
    
def format_percentage(value: float) -> str
    # Display helper
```

---

### 4.9 `config/settings.py`
**Responsibility**: Centralized configuration

**Contents**:
```python
# Ollama Configuration
OLLAMA_MODEL = "llama3"
OLLAMA_BASE_URL = "http://localhost:11434"

# ATS Scoring Weights
KEYWORD_WEIGHT = 0.4
FORMAT_WEIGHT = 0.2
COMPLETENESS_WEIGHT = 0.2
RELEVANCE_WEIGHT = 0.2

# Thresholds
PASSING_ATS_SCORE = 70
MINIMUM_KEYWORD_MATCH = 60

# Keyword Categories
TECHNICAL_KEYWORDS = ["Python", "Java", "AWS", ...]
SOFT_SKILLS = ["Leadership", "Communication", ...]

# Section Headers (for resume parsing)
EDUCATION_HEADERS = ["education", "academic", "qualifications"]
EXPERIENCE_HEADERS = ["experience", "employment", "work history"]
SKILLS_HEADERS = ["skills", "competencies", "technical skills"]
```

---

## 5. Application Workflow

### Step-by-Step Process:

1. **User Input** (`app.py`)
   - Upload resume PDF
   - Paste job description text
   - Click "Analyze" button

2. **Resume Processing**
   - `resume_parser.extract_text_from_pdf()` → raw text
   - `resume_parser.parse_resume_sections()` → structured data

3. **Job Description Processing**
   - `job_description_parser.parse_job_description()` → structured data
   - Extract required/preferred skills

4. **Keyword Analysis**
   - `keyword_matcher.extract_keywords()` for both documents
   - `keyword_matcher.calculate_keyword_match()` → match data

5. **ATS Scoring**
   - `ats_scoring.calculate_ats_score()` → numerical score + breakdown

6. **AI Analysis**
   - `llm_analyzer.generate_improvement_suggestions()` → AI insights
   - `llm_analyzer.analyze_experience_relevance()` → context analysis

7. **Report Generation**
   - `report_generator.generate_full_report()` → complete report
   - Format for display

8. **Display Results** (`app.py`)
   - Show ATS score with visual indicator
   - Display keyword matches (matched/missing)
   - Present AI suggestions
   - Provide action items

---

## 6. Development Roadmap

### Phase 1: Project Setup (Day 1)
- [ ] Create folder structure
- [ ] Initialize Git repository
- [ ] Create `requirements.txt`
- [ ] Setup virtual environment
- [ ] Install dependencies
- [ ] Create `README.md` with setup instructions

### Phase 2: Core Parsing (Day 2-3)
- [ ] Implement `resume_parser.py`
  - PDF text extraction
  - Section identification
  - Contact info extraction
- [ ] Implement `job_description_parser.py`
  - JD text processing
  - Skills extraction
- [ ] Implement `utils.py` (basic functions)
- [ ] Test parsing with sample documents

### Phase 3: Keyword Matching (Day 4)
- [ ] Implement `keyword_matcher.py`
  - Keyword extraction logic
  - Matching algorithm
  - Frequency analysis
- [ ] Create test cases
- [ ] Validate accuracy

### Phase 4: ATS Scoring (Day 5)
- [ ] Implement `ats_scoring.py`
  - Scoring functions for each component
  - Weight calculations
  - Grade assignment logic
- [ ] Test with various resume/JD combinations
- [ ] Fine-tune scoring weights

### Phase 5: LLM Integration (Day 6-7)
- [ ] Setup Ollama locally
- [ ] Test Llama3 model
- [ ] Implement `llm_analyzer.py`
  - Prompt templates
  - API integration
  - Response parsing
- [ ] Test AI suggestions quality
- [ ] Refine prompts

### Phase 6: Report Generation (Day 8)
- [ ] Implement `report_generator.py`
  - Data aggregation
  - Format functions
  - Export capabilities
- [ ] Design report structure

### Phase 7: Streamlit UI (Day 9-10)
- [ ] Build `app.py`
  - Layout design
  - Input widgets
  - Result display components
- [ ] Add styling and visual indicators
- [ ] Implement error handling
- [ ] Add loading states

### Phase 8: Integration & Testing (Day 11-12)
- [ ] Connect all modules in workflow
- [ ] End-to-end testing
- [ ] Handle edge cases
- [ ] Fix bugs
- [ ] Performance optimization

### Phase 9: Documentation & Polish (Day 13-14)
- [ ] Complete README with:
  - Setup instructions
  - Usage guide
  - Screenshots
  - Architecture diagram
- [ ] Add code comments
- [ ] Create sample test files
- [ ] Record demo video (optional)
- [ ] Prepare for portfolio

---

## 7. Key Features

### Core Features:
1. **PDF Resume Upload & Parsing**
2. **Job Description Analysis**
3. **ATS Compatibility Score (0-100)**
4. **Keyword Match Analysis**
5. **AI-Powered Improvement Suggestions**
6. **Visual Report with Charts**
7. **Missing Keywords Identification**
8. **Actionable Recommendations**

### Nice-to-Have Features (Future):
- Resume template suggestions
- Multiple resume comparison
- Export report as PDF
- Historical tracking
- Resume version comparison

---

## 8. Success Criteria

### Technical Requirements:
- ✅ All modules properly separated
- ✅ Clean, documented code
- ✅ No hardcoded values (use config)
- ✅ Error handling for all inputs
- ✅ Type hints throughout
- ✅ Modular, testable functions

### Functional Requirements:
- ✅ Accurate PDF text extraction
- ✅ Meaningful ATS score (validated logic)
- ✅ Relevant keyword matching
- ✅ Useful AI suggestions
- ✅ Clear, professional UI
- ✅ Fast response time (<30s for full analysis)

### Portfolio Quality:
- ✅ Professional README
- ✅ Clean architecture
- ✅ Demonstrates multiple skills
- ✅ Easy to run locally
- ✅ Impressive demo-worthy results

---

## 9. Sample Data Structures

### Resume Data Object:
```python
{
    "raw_text": "string",
    "sections": {
        "contact": {
            "email": "john@example.com",
            "phone": "+1-234-567-8900",
            "linkedin": "linkedin.com/in/john"
        },
        "education": "B.S. Computer Science...",
        "experience": "Software Engineer at...",
        "skills": ["Python", "Java", "AWS"]
    },
    "total_words": 450,
    "has_clear_sections": True
}
```

### Job Description Data Object:
```python
{
    "raw_text": "string",
    "required_skills": ["Python", "Docker", "AWS"],
    "preferred_skills": ["Kubernetes", "CI/CD"],
    "responsibilities": [...],
    "experience_required": "3-5 years",
    "keywords": [...]
}
```

### Final Report Object:
```python
{
    "timestamp": "2026-07-27T10:30:00",
    "ats_score": {
        "total": 78.5,
        "breakdown": {...},
        "grade": "B+",
        "status": "Pass"
    },
    "keyword_analysis": {
        "match_rate": 75.5,
        "matched": [...],
        "missing": [...]
    },
    "ai_insights": {
        "suggestions": [...],
        "priority_actions": [...]
    }
}
```

---

## 10. Dependencies (`requirements.txt`)

```
streamlit==1.28.0
pdfplumber==0.10.3
PyPDF2==3.0.1
pandas==2.1.3
ollama==0.1.6
requests==2.31.0
python-dotenv==1.0.0
```

---

## 11. Design Principles

### Code Quality:
- **DRY**: Don't Repeat Yourself
- **Single Responsibility**: Each module/function has one job
- **Type Safety**: Use type hints
- **Documentation**: Docstrings for all functions
- **Error Handling**: Graceful failures with user-friendly messages

### User Experience:
- **Simple Interface**: Clean, intuitive UI
- **Fast Feedback**: Loading indicators for long operations
- **Clear Results**: Visual score display, organized sections
- **Actionable**: Specific suggestions, not vague advice

### Portfolio Value:
- **Demonstrates Skills**: AI, NLP, web dev, architecture
- **Practical Application**: Solves real problem
- **Professional Quality**: Production-ready code
- **Easy to Showcase**: Clear demo, good documentation

---

## 12. Potential Challenges & Solutions

### Challenge 1: PDF Text Extraction Accuracy
**Solution**: Use pdfplumber as primary, PyPDF2 as fallback, clean text thoroughly

### Challenge 2: Keyword Matching Too Strict
**Solution**: Implement fuzzy matching, handle synonyms, consider context

### Challenge 3: Ollama/LLM Response Time
**Solution**: Add loading indicators, optimize prompts, use streaming if available

### Challenge 4: ATS Score Calibration
**Solution**: Research real ATS systems, validate with multiple resumes, adjust weights

### Challenge 5: Resume Format Variety
**Solution**: Robust parsing logic, handle multiple formats, graceful degradation

---

## End of Specification

**Next Steps**: Review this specification, provide feedback or approve to begin implementation.
