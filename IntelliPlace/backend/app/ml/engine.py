"""Recommendation and skill-gap engine: TF-IDF + cosine similarity + skill coverage + rule eligibility."""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

COVERAGE_WEIGHT = 0.6    # share of score from exact skill coverage
SIMILARITY_WEIGHT = 0.4  # share of score from TF-IDF cosine similarity


def _job_text(job: dict) -> str:
    return " ".join(job["skills"] + [job["title"], job["category"], job["description"]])


def skill_gap(student_skills: list[str], job: dict) -> dict:
    student = {s.strip().lower() for s in student_skills if s and s.strip()}
    required = [s.strip() for s in job["skills"]]
    matched = [s for s in required if s.lower() in student]
    missing = [s for s in required if s.lower() not in student]
    coverage = round(100 * len(matched) / len(required), 1) if required else 0.0
    return {
        "matched_skills": matched,
        "missing_skills": missing,
        "skill_coverage": coverage,
        "skill_gap": round(100 - coverage, 1),
        "learning_sequence": missing,  # learn in the order the job lists them
    }


def is_eligible(profile: dict, job: dict) -> tuple[bool, list[str]]:
    reasons = []
    if profile["cgpa"] < job["min_cgpa"]:
        reasons.append(f"CGPA below required {job['min_cgpa']}")
    branches = {b.lower() for b in job["branches"]}
    if "any" not in branches and profile["branch"].lower() not in branches:
        reasons.append("Branch not in eligible list")
    if profile["backlogs"] > job["max_backlogs"]:
        reasons.append(f"More than {job['max_backlogs']} backlog(s)")
    return (not reasons), reasons


def recommend(profile: dict, jobs: list[dict]) -> list[dict]:
    student_skills = profile["skills"]
    student_text = " ".join(student_skills + [profile.get("career_interests", "")])
    docs = [_job_text(j) for j in jobs] + [student_text]
    try:
        matrix = TfidfVectorizer(stop_words="english").fit_transform(docs)
        sims = cosine_similarity(matrix[-1], matrix[:-1])[0]
    except ValueError:  # no usable tokens (e.g. empty profile)
        sims = [0.0] * len(jobs)

    results = []
    for job, sim in zip(jobs, sims):
        gap = skill_gap(student_skills, job)
        eligible, reasons = is_eligible(profile, job)
        score = 100 * (COVERAGE_WEIGHT * gap["skill_coverage"] / 100 + SIMILARITY_WEIGHT * float(sim))
        results.append({
            "job_id": job["id"],
            "title": job["title"],
            "company": job["company"],
            "location": job["location"],
            "category": job["category"],
            "match_percentage": round(score, 1),
            "eligible": eligible,
            "ineligibility_reasons": reasons,
            "matching_skills": gap["matched_skills"],
            "missing_skills": gap["missing_skills"],
            "explanation": (f"Matches {len(gap['matched_skills'])} of {len(job['skills'])} required skills; "
                            f"profile text similarity {float(sim):.2f}."),
        })
    results.sort(key=lambda r: (r["eligible"], r["match_percentage"]), reverse=True)
    return results
