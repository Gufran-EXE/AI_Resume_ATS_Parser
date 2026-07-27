# ============================================================
# modules/keyword_matcher.py
#
# Responsibility: Rule-based keyword extraction and matching.
# No LLM is called — everything is dictionary + regex based.
#
# Public API
# ----------
# extract_keywords(text: str)              -> KeywordResult
# match_keywords(resume_kw, jd_kw)         -> MatchResult
#
# KeywordResult  (TypedDict)
#   by_category  dict[str, list[str]]  — keywords grouped by category
#   all_keywords list[str]             — flat deduplicated list
#
# MatchResult    (TypedDict)
#   matched      list[str]   — keywords found in both resume and JD
#   missing      list[str]   — JD keywords absent from resume
#   extra        list[str]   — resume keywords not in JD (bonus signal)
#   match_pct    float       — matched / total_jd_keywords * 100
# ============================================================

from __future__ import annotations

import logging
import re
from typing import TypedDict

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Keyword taxonomy
# Each entry is the canonical display name.  The matcher also builds
# lowercase aliases automatically, so spelling variants are handled.
# Multi-word entries (e.g. "Machine Learning") are matched as phrases.
# ─────────────────────────────────────────────────────────────────────────────

KEYWORD_TAXONOMY: dict[str, list[str]] = {

    # ── Programming Languages ──────────────────────────────────────────────
    "Programming Languages": [
        "Python", "Java", "JavaScript", "TypeScript", "C", "C++", "C#",
        "Go", "Golang", "Rust", "Ruby", "PHP", "Swift", "Kotlin", "Scala",
        "R", "MATLAB", "Perl", "Bash", "Shell", "PowerShell", "Groovy",
        "Dart", "Elixir", "Haskell", "Lua", "Julia", "COBOL", "Fortran",
        "Assembly", "Objective-C", "VBA", "SQL", "PL/SQL", "T-SQL",
    ],

    # ── Web Frameworks ─────────────────────────────────────────────────────
    "Frameworks": [
        "Django", "Flask", "FastAPI", "Spring", "Spring Boot", "Express",
        "Node.js", "Next.js", "Nuxt.js", "React", "Vue", "Vue.js",
        "Angular", "Svelte", "Rails", "Ruby on Rails", "Laravel", "Symfony",
        "ASP.NET", ".NET", ".NET Core", "Gin", "Echo", "Fiber",
        "Tornado", "Starlette", "Pyramid", "Bottle", "Falcon",
        "React Native", "Flutter", "Ionic", "Electron",
        "Hibernate", "JPA", "MyBatis", "Sequelize", "SQLAlchemy",
        "GraphQL", "REST", "RESTful", "gRPC", "WebSocket",
        "Celery", "RabbitMQ", "Kafka", "Airflow",
    ],

    # ── Databases ──────────────────────────────────────────────────────────
    "Databases": [
        "MySQL", "PostgreSQL", "SQLite", "Oracle", "SQL Server",
        "MongoDB", "Redis", "Cassandra", "DynamoDB", "Elasticsearch",
        "Neo4j", "CouchDB", "Firebase", "Firestore", "Supabase",
        "MariaDB", "InfluxDB", "TimescaleDB", "Snowflake", "BigQuery",
        "Redshift", "Hive", "HBase", "Couchbase", "RethinkDB",
        "Memcached", "RabbitMQ", "ActiveMQ",
    ],

    # ── Cloud Technologies ─────────────────────────────────────────────────
    "Cloud Technologies": [
        "AWS", "Amazon Web Services", "Azure", "GCP", "Google Cloud",
        "Google Cloud Platform", "Heroku", "DigitalOcean", "Linode",
        "Vercel", "Netlify", "Cloudflare",
        "EC2", "S3", "Lambda", "RDS", "ECS", "EKS", "Fargate",
        "CloudFront", "Route 53", "IAM", "VPC", "SQS", "SNS",
        "Azure DevOps", "Azure Functions", "Azure Blob",
        "GKE", "Cloud Run", "Cloud Functions", "BigQuery",
        "Terraform", "Pulumi", "CloudFormation",
    ],

    # ── Developer Tools ────────────────────────────────────────────────────
    "Developer Tools": [
        "Git", "GitHub", "GitLab", "Bitbucket", "SVN",
        "Docker", "Kubernetes", "Helm", "Podman",
        "Jenkins", "GitHub Actions", "GitLab CI", "CircleCI",
        "Travis CI", "TeamCity", "ArgoCD", "Tekton",
        "CI/CD", "DevOps", "SRE",
        "Ansible", "Chef", "Puppet", "SaltStack",
        "Nginx", "Apache", "Caddy", "HAProxy",
        "Linux", "Unix", "Ubuntu", "CentOS", "Debian",
        "Vagrant", "VirtualBox", "VMware",
        "JIRA", "Confluence", "Trello", "Notion",
        "VS Code", "IntelliJ", "PyCharm", "Eclipse",
        "Postman", "Swagger", "OpenAPI",
        "Prometheus", "Grafana", "Datadog", "Splunk", "ELK",
        "Elasticsearch", "Logstash", "Kibana",
        "Webpack", "Vite", "Babel", "ESLint", "Prettier",
        "npm", "yarn", "pip", "Maven", "Gradle",
    ],

    # ── Libraries ──────────────────────────────────────────────────────────
    "Libraries": [
        "NumPy", "Pandas", "Matplotlib", "Seaborn", "Plotly",
        "Scikit-learn", "TensorFlow", "PyTorch", "Keras",
        "Hugging Face", "Transformers", "OpenCV", "Pillow",
        "NLTK", "spaCy", "Gensim", "LangChain",
        "SciPy", "Statsmodels", "XGBoost", "LightGBM", "CatBoost",
        "Requests", "httpx", "aiohttp", "BeautifulSoup", "Scrapy",
        "Selenium", "Playwright", "Pytest", "unittest", "Jest",
        "Redux", "Zustand", "MobX", "Axios", "Lodash",
        "Pydantic", "Marshmallow", "Alembic",
        "OpenAI", "Anthropic", "LlamaIndex",
        "Boto3", "Paramiko", "Fabric",
        "JWT", "OAuth", "Passlib", "bcrypt",
    ],

    # ── Soft Skills ────────────────────────────────────────────────────────
    "Soft Skills": [
        "Communication", "Teamwork", "Collaboration", "Leadership",
        "Problem Solving", "Problem-solving", "Critical Thinking",
        "Adaptability", "Time Management", "Project Management",
        "Agile", "Scrum", "Kanban", "Waterfall",
        "Attention to Detail", "Analytical", "Creative",
        "Self-motivated", "Self-starter", "Fast Learner",
        "Mentoring", "Coaching", "Presentation", "Documentation",
        "Cross-functional", "Stakeholder", "Client-facing",
        "Ownership", "Accountability", "Initiative",
        "Remote Work", "Distributed Teams",
    ],
}

# Flat set of all canonical names for quick membership checks
_ALL_CANONICAL: set[str] = {
    kw for keywords in KEYWORD_TAXONOMY.values() for kw in keywords
}

# ─────────────────────────────────────────────────────────────────────────────
# Return types
# ─────────────────────────────────────────────────────────────────────────────

class KeywordResult(TypedDict):
    by_category: dict[str, list[str]]
    all_keywords: list[str]


class MatchResult(TypedDict):
    matched: list[str]
    missing: list[str]
    extra: list[str]
    match_pct: float


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _build_pattern(keyword: str) -> re.Pattern:
    """
    Compile a case-insensitive whole-word regex pattern for a keyword.

    Special handling:
    - ``C++``, ``C#``, ``.NET`` — characters that need escaping but must
      still match as complete tokens.
    - Multi-word phrases — matched as exact sequences with flexible
      internal whitespace (handles line-wrapped JDs).
    - Single words — wrapped in word boundaries (\\b).
    """
    escaped = re.escape(keyword)

    # Multi-word: allow flexible whitespace between words
    if " " in keyword:
        escaped = re.sub(r"\\ ", r"\\s+", escaped)
        pattern = escaped
    else:
        # Wrap in word boundary; also handle slash-separated tokens like CI/CD
        pattern = r"(?<![A-Za-z0-9_#@])" + escaped + r"(?![A-Za-z0-9_])"

    return re.compile(pattern, re.IGNORECASE)


# Pre-compile all patterns once at import time — avoids recompiling on every call
_COMPILED_PATTERNS: dict[str, tuple[str, re.Pattern]] = {
    kw: (category, _build_pattern(kw))
    for category, keywords in KEYWORD_TAXONOMY.items()
    for kw in keywords
}


def _scan_text(text: str) -> dict[str, list[str]]:
    """
    Scan *text* for every keyword in the taxonomy.

    Returns a dict mapping category -> sorted list of matched canonical names.
    Deduplication is done per category (case-insensitive).
    """
    found: dict[str, set[str]] = {cat: set() for cat in KEYWORD_TAXONOMY}

    for canonical, (category, pattern) in _COMPILED_PATTERNS.items():
        if pattern.search(text):
            found[category].add(canonical)

    # Convert sets to sorted lists; drop empty categories
    return {
        cat: sorted(keywords)
        for cat, keywords in found.items()
        if keywords
    }


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def extract_keywords(text: str) -> KeywordResult:
    """
    Extract technical and soft-skill keywords from *text* using
    rule-based pattern matching against the built-in taxonomy.

    No LLM is used.  All matching is done with pre-compiled regex patterns.

    Parameters
    ----------
    text : str
        Cleaned text from either ``resume_parser.parse_resume()`` or
        ``job_description_parser.parse_job_description()``.

    Returns
    -------
    KeywordResult
        ``by_category``  — dict mapping each category name to a sorted
                           list of matched keywords found in *text*.
        ``all_keywords`` — flat deduplicated sorted list of all matches.
    """
    if not text or not text.strip():
        logger.debug("extract_keywords received empty text.")
        return KeywordResult(by_category={}, all_keywords=[])

    by_category = _scan_text(text)

    all_keywords: list[str] = sorted(
        {kw for keywords in by_category.values() for kw in keywords}
    )

    logger.info(
        "extract_keywords: found %d keywords across %d categories.",
        len(all_keywords),
        len(by_category),
    )

    return KeywordResult(by_category=by_category, all_keywords=all_keywords)


def match_keywords(
    resume_kw: KeywordResult,
    jd_kw: KeywordResult,
) -> MatchResult:
    """
    Compare resume keywords against job-description keywords.

    Parameters
    ----------
    resume_kw : KeywordResult
        Output of ``extract_keywords()`` run on the resume text.
    jd_kw : KeywordResult
        Output of ``extract_keywords()`` run on the JD text.

    Returns
    -------
    MatchResult
        ``matched``   — keywords present in both resume and JD.
        ``missing``   — JD keywords absent from the resume (gaps to fill).
        ``extra``     — resume keywords not required by the JD (bonus skills).
        ``match_pct`` — percentage of JD keywords found in the resume
                        (0.0 if JD has no keywords).
    """
    resume_set = set(resume_kw["all_keywords"])
    jd_set = set(jd_kw["all_keywords"])

    matched = sorted(resume_set & jd_set)
    missing = sorted(jd_set - resume_set)
    extra   = sorted(resume_set - jd_set)

    match_pct = (len(matched) / len(jd_set) * 100) if jd_set else 0.0

    logger.info(
        "match_keywords: matched=%d  missing=%d  extra=%d  pct=%.1f%%",
        len(matched), len(missing), len(extra), match_pct,
    )

    return MatchResult(
        matched=matched,
        missing=missing,
        extra=extra,
        match_pct=round(match_pct, 1),
    )
