import os
import sys
import uuid

os.environ["DATABASE_URL"] = "sqlite:///./test_intelliplace.db"
os.environ["GEMINI_API_KEY"] = ""  # tests always use the question bank
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.ml.engine import skill_gap, is_eligible, recommend  # noqa: E402
from app.ml.jobs_data import JOBS  # noqa: E402
from app.resume_service import analyze_ats, detect_skills, extract_text, ResumeError  # noqa: E402
from app.services import evaluate_interview, grade_mock, readiness, build_roadmap  # noqa: E402
from app.ai_service import AIError, generate_mcqs, validate_mcqs, validate_interview  # noqa: E402
from app import session_store  # noqa: E402

client = TestClient(app)

SAMPLE_RESUME = """Rahul Sharma
rahul@example.com | +91 9876543210 | linkedin.com/in/rahul | github.com/rahul

Summary
Data enthusiast with skills in Python, SQL and Pandas.

Education
B.Tech in Computer Science, ITM University, 2027

Skills
Python, SQL, Pandas, NumPy, Excel, Power BI, Git, Machine Learning, Statistics, Communication

Projects
Built a sales dashboard using Pandas and Power BI, improved reporting time by 40%.
Developed a churn model with 85% accuracy on 10000 records.
Automated data cleaning, reducing manual effort by 60%.

Internship
Analyzed 5000 rows of customer data and delivered weekly reports.

Certifications
Google Data Analytics Certificate, 2025
"""


def _register(email=None):
    email = email or f"student_{uuid.uuid4().hex[:8]}@example.com"
    res = client.post("/api/auth/register", json={
        "full_name": "Test Student", "email": email, "password": "StrongPass123",
        "college": "Demo College", "degree": "B.Tech", "branch": "CSE", "graduation_year": 2027})
    assert res.status_code == 201, res.text
    return email, res.json()["access_token"]


def _h(token):
    return {"Authorization": f"Bearer {token}"}


# ---------- engine ----------
def test_skill_gap_counts_matches_and_coverage():
    r = skill_gap(["python", "sql"], {"skills": ["Python", "SQL", "Power BI"]})
    assert r["matched_skills"] == ["Python", "SQL"]
    assert r["missing_skills"] == ["Power BI"]
    assert r["skill_coverage"] == 66.7


def test_eligibility_rules():
    job = {"min_cgpa": 7.0, "branches": ["CSE"], "max_backlogs": 0}
    ok, _ = is_eligible({"cgpa": 8.0, "branch": "cse", "backlogs": 0}, job)
    assert ok
    ok, reasons = is_eligible({"cgpa": 6.0, "branch": "ECE", "backlogs": 1}, job)
    assert not ok and len(reasons) == 3


def test_recommend_puts_eligible_jobs_first():
    profile = {"skills": ["Python", "SQL", "Pandas", "Excel"], "cgpa": 8.0,
               "branch": "CSE", "backlogs": 0, "career_interests": "data analysis"}
    recs = recommend(profile, JOBS)
    assert len(recs) == len(JOBS)
    flags = [r["eligible"] for r in recs]
    assert flags == sorted(flags, reverse=True)


def test_recommend_empty_profile_scores_are_zero():
    profile = {"skills": [], "cgpa": 0, "branch": "", "backlogs": 0, "career_interests": ""}
    assert all(r["match_percentage"] == 0.0 for r in recommend(profile, JOBS))


# ---------- resume & ATS ----------
def test_detect_skills_and_ats_on_sample_resume():
    skills = detect_skills(SAMPLE_RESUME)
    assert "Python" in skills and "SQL" in skills and "Power BI" in skills
    ats = analyze_ats(SAMPLE_RESUME, skills)
    assert 0 <= ats["score"] <= 100
    assert ats["info"]["email"] == "rahul@example.com"
    assert ats["info"]["has_linkedin"] is True


def test_extract_text_rejects_bad_files():
    for name, data in [("cv.exe", b"x" * 100), ("cv.txt", b""), ("cv.txt", b"short")]:
        try:
            extract_text(name, data)
            assert False, "should have raised"
        except ResumeError:
            pass


def test_resume_upload_and_get():
    _, token = _register()
    res = client.post("/api/resume/upload", headers=_h(token),
                      files={"file": ("cv.txt", SAMPLE_RESUME.encode(), "text/plain")})
    assert res.status_code == 201, res.text
    body = res.json()
    assert "Python" in body["skills"] and body["ats"]["score"] > 0
    got = client.get("/api/resume", headers=_h(token)).json()
    assert got["uploaded"] is True and got["filename"] == "cv.txt"


def test_bad_resume_upload_is_rejected():
    _, token = _register()
    res = client.post("/api/resume/upload", headers=_h(token),
                      files={"file": ("cv.exe", b"binary", "application/octet-stream")})
    assert res.status_code == 400


def test_resume_skills_feed_recommendations():
    _, token = _register()
    client.post("/api/resume/upload", headers=_h(token),
                files={"file": ("cv.txt", SAMPLE_RESUME.encode(), "text/plain")})
    recs = client.get("/api/jobs/recommendations", headers=_h(token)).json()
    assert any(r["matching_skills"] for r in recs)


# ---------- mock test & interview (question bank path, AI disabled in tests) ----------
def test_ai_is_disabled_in_tests():
    assert client.get("/api/ai/status").json()["ai_enabled"] is False


def test_mock_questions_hide_answers_and_submit_works():
    _, token = _register()
    data = client.get("/api/mock-test/questions", params={"category": "python"}).json()
    assert data["source"] == "bank" and data["set_id"]
    assert len(data["questions"]) == 8 and "answer" not in data["questions"][0]
    answers = {str(q["id"]): 0 for q in data["questions"]}
    res = client.post("/api/mock-test/submit", headers=_h(token),
                      json={"set_id": data["set_id"], "answers": answers})
    assert res.status_code == 200 and len(res.json()["review"]) == 8
    assert len(client.get("/api/mock-test/history", headers=_h(token)).json()) == 1


def test_mock_perfect_score_uses_server_answers():
    data = client.get("/api/mock-test/questions", params={"category": "sql"}).json()
    items = session_store.get(data["set_id"], "mock")["items"]
    perfect = {str(i): x["answer"] for i, x in enumerate(items)}
    assert grade_mock(data["set_id"], perfect)["score"] == 100.0


def test_expired_or_unknown_test_set_is_rejected():
    _, token = _register()
    res = client.post("/api/mock-test/submit", headers=_h(token), json={"set_id": "nope", "answers": {}})
    assert res.status_code == 410


def test_interview_flow_and_scoring():
    _, token = _register()
    data = client.get("/api/interview/questions").json()
    assert data["source"] == "bank" and len(data["questions"]) == 8
    items = session_store.get(data["set_id"], "interview")["items"]
    keyword_answer = "I can explain this clearly: " + " and ".join(items[0]["keywords"]) + ". " + "It matters because " * 3
    good = client.post("/api/interview/evaluate", headers=_h(token),
                       json={"set_id": data["set_id"], "question_id": 0, "answer": keyword_answer})
    assert good.status_code == 200 and good.json()["score"] == 100.0
    short = client.post("/api/interview/evaluate", headers=_h(token),
                        json={"set_id": data["set_id"], "question_id": 0, "answer": "list"})
    assert short.json()["score"] <= 60
    assert client.post("/api/interview/evaluate", headers=_h(token),
                       json={"set_id": data["set_id"], "question_id": 99, "answer": "x"}).status_code == 404


def test_generate_raises_without_key():
    try:
        generate_mcqs("Python")
        assert False, "should have raised"
    except AIError:
        pass


def test_validate_mcqs_keeps_only_good_items():
    good = {"question": "Q?", "options": ["a", "b", "c", "d"], "answer": 2}
    bad_count = {"question": "Q?", "options": ["a", "b", "c"], "answer": 0}
    bad_index = {"question": "Q?", "options": ["a", "b", "c", "d"], "answer": 9}
    dup = {"question": "Q?", "options": ["a", "a", "c", "d"], "answer": 0}
    out = validate_mcqs([good] * 5 + [bad_count, bad_index, dup])
    assert len(out) == 5 and out[0]["answer"] == 2


def test_validate_mcqs_rejects_too_few():
    try:
        validate_mcqs([{"question": "Q?", "options": ["a", "b", "c", "d"], "answer": 0}])
        assert False, "should have raised"
    except AIError:
        pass


def test_validate_interview_normalizes_keywords():
    items = [{"question": "Q?", "keywords": ["Mutable", "LIST"], "tip": "t"}] * 5
    out = validate_interview(items)
    assert out[0]["keywords"] == ["mutable", "list"]


# ---------- roadmap, plan, readiness ----------
def test_roadmap_and_empty_roadmap_message():
    assert build_roadmap([])["message"] == "" or build_roadmap([])["weeks"] == []
    recs = [{"missing_skills": ["Power BI", "Excel"]}, {"missing_skills": ["Power BI"]}]
    weeks = build_roadmap(recs)["weeks"]
    assert weeks[0]["focus"] == "Power BI"


def test_readiness_score_range():
    r = readiness(100, 80, [{"match_percentage": 70}] * 3, [{"score": 60}], [{"score": 50}])
    assert 0 <= r["score"] <= 100 and len(r["components"]) == 5


def test_progress_and_action_plan_endpoints():
    _, token = _register()
    prog = client.get("/api/progress", headers=_h(token)).json()
    assert prog["total"] == 10 and "readiness" in prog
    plan = client.get("/api/action-plan", headers=_h(token)).json()
    assert len(plan["steps"]) >= 1
    assert client.get("/api/roadmap", headers=_h(token)).status_code == 200


# ---------- auth & profile (existing behaviour) ----------
def test_auth_flow_and_duplicate_email():
    email, token = _register()
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers=_h(token)).json()["email"] == email
    assert client.post("/api/auth/register", json={"full_name": "Dup Name", "email": email,
                                                   "password": "StrongPass123"}).status_code == 409
    assert client.post("/api/auth/login", json={"email": email, "password": "wrong-password"}).status_code == 401


def test_profile_null_values_do_not_crash():
    _, token = _register()
    res = client.put("/api/profile", headers=_h(token), json={"full_name": None, "skills": None})
    assert res.status_code == 200 and res.json()["skills"] == []


def test_saved_jobs_and_gap_analysis():
    _, token = _register()
    h = _h(token)
    assert client.post("/api/jobs/1/save", headers=h).status_code == 201
    assert any(j["id"] == 1 for j in client.get("/api/jobs/saved", headers=h).json())
    assert client.delete("/api/jobs/1/save", headers=h).status_code == 200
    assert client.post("/api/skills/gap-analysis", headers=h, json={"job_id": 1}).status_code == 200
    assert client.get("/api/jobs/999", headers=h).status_code == 404


def test_web_page_is_served():
    res = client.get("/")
    assert res.status_code == 200 and "IntelliPlace" in res.text
