# ============================================================
# modules/skill_recommender.py
#
# Responsibility: Rule-based skill recommendations derived
# purely from missing keywords and JD category data.
# No LLM, no hallucination — every recommendation is grounded
# in what the JD actually demands and what the resume lacks.
#
# Public API
# ----------
# recommend_skills(missing_kw, jd_kw) -> SkillRecommendations
#
# SkillRecommendations (TypedDict)
#   technologies   list[Recommendation]
#   frameworks     list[Recommendation]
#   certifications list[Recommendation]
#   projects       list[Recommendation]
#
# Recommendation (TypedDict)
#   name    str   — what to learn / do
#   reason  str   — why (grounded in JD data)
#   priority str  — "High" | "Medium" | "Low"
# ============================================================

from __future__ import annotations

import logging
from typing import TypedDict

from modules.keyword_matcher import KeywordResult

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Return types
# ─────────────────────────────────────────────────────────────────────────────

class Recommendation(TypedDict):
    name:     str
    reason:   str
    priority: str   # "High" | "Medium" | "Low"


class SkillRecommendations(TypedDict):
    technologies:   list[Recommendation]
    frameworks:     list[Recommendation]
    certifications: list[Recommendation]
    projects:       list[Recommendation]


# ─────────────────────────────────────────────────────────────────────────────
# Knowledge base
#
# Each entry maps a MISSING keyword to a concrete recommendation.
# Keys are lowercase for case-insensitive lookup.
# This knowledge base is curated — nothing is invented at runtime.
# ─────────────────────────────────────────────────────────────────────────────

# technology recommendations keyed by missing skill (lowercase)
_TECH_RECOMMENDATIONS: dict[str, Recommendation] = {
    "docker": Recommendation(
        name="Docker",
        reason="Container skills are required by this role. Learn image building, volumes, and compose.",
        priority="High",
    ),
    "kubernetes": Recommendation(
        name="Kubernetes",
        reason="Orchestration is listed in the JD. Start with minikube to practise locally.",
        priority="High",
    ),
    "aws": Recommendation(
        name="AWS Core Services",
        reason="Cloud platform required by the JD. Focus on EC2, S3, IAM, and Lambda.",
        priority="High",
    ),
    "amazon web services": Recommendation(
        name="AWS Core Services",
        reason="Cloud platform required by the JD. Focus on EC2, S3, IAM, and Lambda.",
        priority="High",
    ),
    "azure": Recommendation(
        name="Microsoft Azure",
        reason="Azure is mentioned in the JD. Start with Azure Portal, VMs, and Blob Storage.",
        priority="High",
    ),
    "gcp": Recommendation(
        name="Google Cloud Platform",
        reason="GCP is required by this role. Begin with Cloud Run, BigQuery, and GKE.",
        priority="High",
    ),
    "google cloud": Recommendation(
        name="Google Cloud Platform",
        reason="GCP is required by this role. Begin with Cloud Run, BigQuery, and GKE.",
        priority="High",
    ),
    "terraform": Recommendation(
        name="Terraform",
        reason="Infrastructure-as-code is in the JD. Practice provisioning AWS/GCP resources.",
        priority="Medium",
    ),
    "ci/cd": Recommendation(
        name="CI/CD Pipelines",
        reason="Automated deployment is expected. Learn GitHub Actions or GitLab CI basics.",
        priority="High",
    ),
    "linux": Recommendation(
        name="Linux / Bash",
        reason="Command-line proficiency is implied. Practice file system, processes, and scripting.",
        priority="Medium",
    ),
    "git": Recommendation(
        name="Git Version Control",
        reason="Git is a baseline requirement. Master branching, merging, and pull-request workflows.",
        priority="High",
    ),
    "redis": Recommendation(
        name="Redis",
        reason="In-memory caching is in the JD. Learn key-value operations and pub/sub basics.",
        priority="Medium",
    ),
    "elasticsearch": Recommendation(
        name="Elasticsearch",
        reason="Search/analytics stack appears in the JD. Practice indexing and querying.",
        priority="Medium",
    ),
    "kafka": Recommendation(
        name="Apache Kafka",
        reason="Event streaming is required. Start with producer/consumer patterns.",
        priority="Medium",
    ),
    "graphql": Recommendation(
        name="GraphQL",
        reason="GraphQL API design is in the JD. Build a small schema with queries and mutations.",
        priority="Medium",
    ),
    "typescript": Recommendation(
        name="TypeScript",
        reason="Strongly-typed JavaScript is required. Convert an existing JS project to TS.",
        priority="Medium",
    ),
    "golang": Recommendation(
        name="Go (Golang)",
        reason="Go is listed as a required language. Work through the official Tour of Go.",
        priority="High",
    ),
    "go": Recommendation(
        name="Go (Golang)",
        reason="Go is listed as a required language. Work through the official Tour of Go.",
        priority="High",
    ),
    "rust": Recommendation(
        name="Rust",
        reason="Systems-level programming is expected. Start with The Rust Book.",
        priority="Medium",
    ),
    "spark": Recommendation(
        name="Apache Spark",
        reason="Big data processing appears in the JD. Practice DataFrames and Spark SQL.",
        priority="Medium",
    ),
    "airflow": Recommendation(
        name="Apache Airflow",
        reason="Workflow orchestration is listed. Build a simple DAG to understand scheduling.",
        priority="Medium",
    ),
    "ansible": Recommendation(
        name="Ansible",
        reason="Configuration management is in the JD. Write playbooks for server provisioning.",
        priority="Low",
    ),
    "prometheus": Recommendation(
        name="Prometheus + Grafana",
        reason="Observability stack is mentioned. Set up metrics collection and a dashboard.",
        priority="Low",
    ),
}

# framework recommendations
_FRAMEWORK_RECOMMENDATIONS: dict[str, Recommendation] = {
    "fastapi": Recommendation(
        name="FastAPI",
        reason="Required framework in the JD. Build a REST API with async endpoints and Pydantic models.",
        priority="High",
    ),
    "django": Recommendation(
        name="Django",
        reason="Full-stack web framework in the JD. Follow the official polls tutorial to start.",
        priority="High",
    ),
    "flask": Recommendation(
        name="Flask",
        reason="Lightweight web framework listed in the JD. Build a REST API with Blueprints.",
        priority="High",
    ),
    "spring boot": Recommendation(
        name="Spring Boot",
        reason="Java backend framework required. Build a REST service with Spring Data JPA.",
        priority="High",
    ),
    "spring": Recommendation(
        name="Spring Framework",
        reason="Java framework is listed. Learn dependency injection and MVC patterns.",
        priority="High",
    ),
    "react": Recommendation(
        name="React",
        reason="Frontend framework in the JD. Build a small SPA with hooks and context.",
        priority="High",
    ),
    "next.js": Recommendation(
        name="Next.js",
        reason="SSR/SSG framework required. Start with the official Next.js tutorial.",
        priority="High",
    ),
    "node.js": Recommendation(
        name="Node.js",
        reason="Server-side JS runtime listed in JD. Build an Express REST API.",
        priority="High",
    ),
    "angular": Recommendation(
        name="Angular",
        reason="Frontend framework required. Build a component-based app with RxJS.",
        priority="Medium",
    ),
    "vue": Recommendation(
        name="Vue.js",
        reason="Progressive framework listed in JD. Build a reactive UI with Composition API.",
        priority="Medium",
    ),
    "vue.js": Recommendation(
        name="Vue.js",
        reason="Progressive framework listed in JD. Build a reactive UI with Composition API.",
        priority="Medium",
    ),
    "celery": Recommendation(
        name="Celery",
        reason="Async task queue is in the JD. Integrate with Redis broker for background jobs.",
        priority="Medium",
    ),
    "sqlalchemy": Recommendation(
        name="SQLAlchemy",
        reason="ORM listed in the JD. Learn session management and relationship mapping.",
        priority="Medium",
    ),
    "pytorch": Recommendation(
        name="PyTorch",
        reason="Deep learning framework in the JD. Implement a simple neural network.",
        priority="Medium",
    ),
    "tensorflow": Recommendation(
        name="TensorFlow / Keras",
        reason="ML framework required. Build and train a classification model.",
        priority="Medium",
    ),
    "scikit-learn": Recommendation(
        name="Scikit-learn",
        reason="ML library is in the JD. Practice supervised and unsupervised learning pipelines.",
        priority="Medium",
    ),
}

# certification recommendations keyed by skill area
_CERT_RECOMMENDATIONS: dict[str, Recommendation] = {
    "aws": Recommendation(
        name="AWS Certified Solutions Architect – Associate",
        reason="Direct match to AWS requirement in the JD. Widely recognised by hiring managers.",
        priority="High",
    ),
    "amazon web services": Recommendation(
        name="AWS Certified Developer – Associate",
        reason="Validates AWS skills required by this role.",
        priority="High",
    ),
    "azure": Recommendation(
        name="Microsoft Certified: Azure Developer Associate (AZ-204)",
        reason="Validates Azure skills required by this role.",
        priority="High",
    ),
    "gcp": Recommendation(
        name="Google Associate Cloud Engineer",
        reason="Validates GCP skills required by this role.",
        priority="High",
    ),
    "google cloud": Recommendation(
        name="Google Associate Cloud Engineer",
        reason="Validates GCP skills required by this role.",
        priority="High",
    ),
    "kubernetes": Recommendation(
        name="Certified Kubernetes Application Developer (CKAD)",
        reason="Industry-standard K8s cert aligned with the JD requirement.",
        priority="High",
    ),
    "docker": Recommendation(
        name="Docker Certified Associate (DCA)",
        reason="Validates container skills expected by this role.",
        priority="Medium",
    ),
    "ci/cd": Recommendation(
        name="GitHub Actions / GitLab CI Certification",
        reason="Certifies pipeline automation skills listed in the JD.",
        priority="Medium",
    ),
    "terraform": Recommendation(
        name="HashiCorp Certified: Terraform Associate",
        reason="Validates IaC skills required by the JD.",
        priority="Medium",
    ),
    "python": Recommendation(
        name="PCEP / PCAP — Python Institute Certifications",
        reason="Certifies Python proficiency, a core requirement.",
        priority="Low",
    ),
    "java": Recommendation(
        name="Oracle Certified Professional: Java SE Developer",
        reason="Validates Java skills required by the JD.",
        priority="Medium",
    ),
    "machine learning": Recommendation(
        name="TensorFlow Developer Certificate",
        reason="Practical ML certification aligned with data science roles.",
        priority="Medium",
    ),
    "devops": Recommendation(
        name="DevOps Institute DASA or AWS DevOps Professional",
        reason="Validates end-to-end DevOps practices expected in this role.",
        priority="Medium",
    ),
    "agile": Recommendation(
        name="PSM I — Professional Scrum Master",
        reason="Widely respected Agile certification for process-oriented roles.",
        priority="Low",
    ),
}

# project ideas keyed by skill area
_PROJECT_RECOMMENDATIONS: dict[str, Recommendation] = {
    "docker": Recommendation(
        name="Dockerise an existing web application",
        reason="Demonstrates containerisation hands-on. Add a multi-stage Dockerfile and compose file.",
        priority="High",
    ),
    "kubernetes": Recommendation(
        name="Deploy a microservices app on minikube",
        reason="Shows K8s deployment, services, and ingress — directly matching the JD.",
        priority="High",
    ),
    "aws": Recommendation(
        name="Build a serverless REST API on AWS Lambda + API Gateway",
        reason="Covers core AWS services required by the JD with a portfolio-ready project.",
        priority="High",
    ),
    "amazon web services": Recommendation(
        name="Build a serverless REST API on AWS Lambda + API Gateway",
        reason="Covers core AWS services required by the JD with a portfolio-ready project.",
        priority="High",
    ),
    "fastapi": Recommendation(
        name="Build a production-ready REST API with FastAPI",
        reason="Directly demonstrates the required framework with async endpoints, auth, and docs.",
        priority="High",
    ),
    "react": Recommendation(
        name="Build a full-stack app with React + REST API",
        reason="Shows frontend skills expected in the JD. Add auth and deploy to Vercel.",
        priority="High",
    ),
    "ci/cd": Recommendation(
        name="Set up a CI/CD pipeline with GitHub Actions",
        reason="Automates test → build → deploy — exactly what the JD requires.",
        priority="High",
    ),
    "machine learning": Recommendation(
        name="End-to-end ML project on Kaggle dataset",
        reason="Shows data prep, modelling, and evaluation in a single notebook or app.",
        priority="Medium",
    ),
    "redis": Recommendation(
        name="Add Redis caching to an existing API",
        reason="Demonstrates performance optimisation — a practical use of the required skill.",
        priority="Medium",
    ),
    "kafka": Recommendation(
        name="Build a real-time event pipeline with Kafka",
        reason="Producer → topic → consumer pattern directly demonstrates the JD requirement.",
        priority="Medium",
    ),
    "terraform": Recommendation(
        name="Provision cloud infrastructure with Terraform",
        reason="IaC project using modules and remote state — strong portfolio signal.",
        priority="Medium",
    ),
    "graphql": Recommendation(
        name="Replace a REST API with a GraphQL schema",
        reason="Shows query design, resolvers, and mutations — directly matches JD.",
        priority="Medium",
    ),
    "typescript": Recommendation(
        name="Migrate a JavaScript project to TypeScript",
        reason="Demonstrates type safety and tooling — a valued skill in this role.",
        priority="Medium",
    ),
    "elasticsearch": Recommendation(
        name="Build a full-text search feature with Elasticsearch",
        reason="Indexing + querying real data directly demonstrates the JD requirement.",
        priority="Medium",
    ),
    "airflow": Recommendation(
        name="Build a data pipeline with Apache Airflow",
        reason="DAG-based ETL pipeline shows orchestration skills required by the JD.",
        priority="Medium",
    ),
}

# ─────────────────────────────────────────────────────────────────────────────
# Deduplication helper
# ─────────────────────────────────────────────────────────────────────────────

def _deduplicate(recs: list[Recommendation]) -> list[Recommendation]:
    """Remove duplicate recommendations by name, keeping first occurrence."""
    seen: set[str] = set()
    result: list[Recommendation] = []
    for r in recs:
        if r["name"] not in seen:
            seen.add(r["name"])
            result.append(r)
    return result


def _sort_by_priority(recs: list[Recommendation]) -> list[Recommendation]:
    """Sort High → Medium → Low."""
    order = {"High": 0, "Medium": 1, "Low": 2}
    return sorted(recs, key=lambda r: order.get(r["priority"], 3))


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def recommend_skills(
    missing_keywords: list[str],
    jd_kw: KeywordResult,
) -> SkillRecommendations:
    """
    Generate practical, grounded skill recommendations based on missing keywords.

    Parameters
    ----------
    missing_keywords : list[str]
        Keywords present in the JD but absent from the resume
        (from ``MatchResult["missing"]``).
    jd_kw : KeywordResult
        Full JD keyword result — used to determine which skill categories
        the role emphasises.

    Returns
    -------
    SkillRecommendations
        Four lists (technologies, frameworks, certifications, projects),
        each sorted High → Medium → Low.
        Lists are capped at 6 items each to stay concise.

    Notes
    -----
    * No LLM is used — every recommendation comes from the knowledge base.
    * Only skills that are genuinely missing are recommended.
    * Duplicates across multiple missing keywords are removed.
    """
    techs:  list[Recommendation] = []
    frames: list[Recommendation] = []
    certs:  list[Recommendation] = []
    projs:  list[Recommendation] = []

    for kw in missing_keywords:
        key = kw.lower()

        if key in _TECH_RECOMMENDATIONS:
            techs.append(_TECH_RECOMMENDATIONS[key])

        if key in _FRAMEWORK_RECOMMENDATIONS:
            frames.append(_FRAMEWORK_RECOMMENDATIONS[key])

        if key in _CERT_RECOMMENDATIONS:
            certs.append(_CERT_RECOMMENDATIONS[key])

        if key in _PROJECT_RECOMMENDATIONS:
            projs.append(_PROJECT_RECOMMENDATIONS[key])

    # Also check JD categories for broader cert coverage
    jd_cats_lower = {c.lower() for c in jd_kw["by_category"].keys()}
    if "cloud technologies" in jd_cats_lower:
        for kw in jd_kw["by_category"].get("Cloud Technologies", []):
            key = kw.lower()
            if key in _CERT_RECOMMENDATIONS:
                certs.append(_CERT_RECOMMENDATIONS[key])

    # Clean up
    techs  = _sort_by_priority(_deduplicate(techs))[:6]
    frames = _sort_by_priority(_deduplicate(frames))[:6]
    certs  = _sort_by_priority(_deduplicate(certs))[:5]
    projs  = _sort_by_priority(_deduplicate(projs))[:5]

    logger.info(
        "recommend_skills: techs=%d frameworks=%d certs=%d projects=%d",
        len(techs), len(frames), len(certs), len(projs),
    )

    return SkillRecommendations(
        technologies=techs,
        frameworks=frames,
        certifications=certs,
        projects=projs,
    )
