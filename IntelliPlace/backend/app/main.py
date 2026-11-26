import json
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from . import models
from .content import MOCK_TESTS
from .database import Base, engine, get_db
from .extra_models import InterviewAttempt, Resume, TestAttempt
from .ml.engine import is_eligible, recommend, skill_gap
from .ml.jobs_data import JOBS
from .resume_service import ResumeError, analyze_ats, detect_skills, extract_text
from .security import create_token, current_user, hash_password, verify_password
from .ai_service import ai_enabled
from .services import (build_action_plan, build_roadmap, evaluate_interview, grade_mock,
                       mock_categories, prepare_interview, prepare_mock, readiness)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="IntelliPlace API", version="0.3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- schemas ----------
class RegisterIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=8, max_length=128)
    college: str = ""
    degree: str = ""
    branch: str = ""
    graduation_year: Optional[int] = None


class LoginIn(BaseModel):
    email: str
    password: str


class ProfileIn(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    phone: Optional[str] = None
    college: Optional[str] = None
    degree: Optional[str] = None
    branch: Optional[str] = None
    graduation_year: Optional[int] = None
    cgpa: Optional[float] = Field(default=None, ge=0, le=10)
    backlogs: Optional[int] = Field(default=None, ge=0)
    skills: Optional[list[str]] = None
    career_interests: Optional[str] = None


class GapIn(BaseModel):
    job_id: int


class MockSubmit(BaseModel):
    set_id: str
    answers: dict[str, int]


class InterviewIn(BaseModel):
    set_id: str
    question_id: int
    answer: str = Field(min_length=1, max_length=3000)


# ---------- helpers ----------
def user_out(u: models.User) -> dict:
    return {"id": u.id, "full_name": u.full_name, "email": u.email, "college": u.college,
            "degree": u.degree, "branch": u.branch, "graduation_year": u.graduation_year}


def profile_dict(u: models.User) -> dict:
    return {"skills": json.loads(u.skills or "[]"), "cgpa": u.cgpa or 0.0, "branch": u.branch or "",
            "backlogs": u.backlogs or 0, "career_interests": u.career_interests or ""}


def profile_out(u: models.User) -> dict:
    fields = {"full_name": u.full_name, "phone": u.phone, "college": u.college, "degree": u.degree,
              "branch": u.branch, "graduation_year": u.graduation_year, "cgpa": u.cgpa,
              "backlogs": u.backlogs, "skills": json.loads(u.skills or "[]"),
              "career_interests": u.career_interests}
    filled = sum(1 for v in fields.values() if v not in (None, "", [], 0, 0.0))
    return {**fields, "profile_completion": round(100 * filled / len(fields), 1)}


def latest_resume(db: Session, user: models.User) -> Optional[Resume]:
    return db.query(Resume).filter(Resume.user_id == user.id).order_by(Resume.id.desc()).first()


def effective_profile(user: models.User, db: Session) -> dict:
    """Profile skills merged with skills detected in the latest resume."""
    base = profile_dict(user)
    r = latest_resume(db, user)
    if r:
        seen = {s.lower() for s in base["skills"]}
        base["skills"] = base["skills"] + [s for s in json.loads(r.skills or "[]") if s.lower() not in seen]
    return base


def resume_out(r: Resume) -> dict:
    return {"id": r.id, "filename": r.filename, "skills": json.loads(r.skills or "[]"),
            "ats": json.loads(r.ats_report or "{}"),
            "uploaded_at": r.created_at.isoformat() if r.created_at else None}


def find_job(job_id: int) -> dict:
    job = next((j for j in JOBS if j["id"] == job_id), None)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def mock_history_rows(db: Session, user: models.User) -> list[dict]:
    rows = db.query(TestAttempt).filter(TestAttempt.user_id == user.id).order_by(TestAttempt.id).all()
    return [{"category": r.category, "score": r.score, "correct": r.correct, "total": r.total} for r in rows]


def interview_history(db: Session, user: models.User) -> list[dict]:
    rows = db.query(InterviewAttempt).filter(InterviewAttempt.user_id == user.id).order_by(InterviewAttempt.id).all()
    return [{"question_id": r.question_id, "score": r.score} for r in rows]


# ---------- health ----------
@app.get("/api/health")
def health():
    return {"status": "ok", "jobs": len(JOBS)}


# ---------- auth ----------
@app.post("/api/auth/register", status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.query(models.User).filter(models.User.email == email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    user = models.User(full_name=body.full_name, email=email, password_hash=hash_password(body.password),
                       college=body.college, degree=body.degree, branch=body.branch,
                       graduation_year=body.graduation_year)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"access_token": create_token(user.id), "token_type": "bearer", "user": user_out(user)}


@app.post("/api/auth/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == body.email.lower()).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"access_token": create_token(user.id), "token_type": "bearer", "user": user_out(user)}


@app.get("/api/auth/me")
def me(user: models.User = Depends(current_user)):
    return user_out(user)


# ---------- profile ----------
@app.get("/api/profile")
def get_profile(user: models.User = Depends(current_user)):
    return profile_out(user)


@app.put("/api/profile")
def update_profile(body: ProfileIn, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    for key, value in body.model_dump(exclude_unset=True).items():
        if key == "full_name" and value is None:
            continue
        if key == "skills":
            value = json.dumps(sorted({s.strip() for s in (value or []) if s and s.strip()}, key=str.lower))
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return profile_out(user)


# ---------- resume & ATS ----------
@app.post("/api/resume/upload", status_code=201)
async def upload_resume(file: UploadFile = File(...), user: models.User = Depends(current_user),
                        db: Session = Depends(get_db)):
    data = await file.read()
    try:
        text = extract_text(file.filename or "", data)
    except ResumeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    skills = detect_skills(text)
    ats = analyze_ats(text, skills)
    r = Resume(user_id=user.id, filename=file.filename or "resume", text=text,
               skills=json.dumps(skills), ats_score=ats["score"], ats_report=json.dumps(ats))
    db.add(r)
    db.commit()
    db.refresh(r)
    return resume_out(r)


@app.get("/api/resume")
def get_resume(user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    r = latest_resume(db, user)
    if r is None:
        return {"uploaded": False}
    return {"uploaded": True, **resume_out(r)}


# ---------- jobs ----------
@app.get("/api/jobs")
def list_jobs(search: Optional[str] = None, category: Optional[str] = None,
              location: Optional[str] = None, min_cgpa: Optional[float] = None):
    jobs = JOBS
    if search:
        q = search.lower()
        jobs = [j for j in jobs if q in j["title"].lower() or q in j["company"].lower()]
    if category:
        jobs = [j for j in jobs if j["category"].lower() == category.lower()]
    if location:
        jobs = [j for j in jobs if j["location"].lower() == location.lower()]
    if min_cgpa is not None:
        jobs = [j for j in jobs if j["min_cgpa"] <= min_cgpa]
    return jobs


@app.get("/api/jobs/recommendations")
def job_recommendations(user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    return recommend(effective_profile(user, db), JOBS)


@app.get("/api/jobs/saved")
def saved_jobs(user: models.User = Depends(current_user)):
    saved_ids = {s.job_id for s in user.saved_jobs}
    return [j for j in JOBS if j["id"] in saved_ids]


@app.get("/api/jobs/{job_id}")
def job_detail(job_id: int, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    job = find_job(job_id)
    profile = effective_profile(user, db)
    eligible, reasons = is_eligible(profile, job)
    return {**job, "student_analysis": skill_gap(profile["skills"], job),
            "eligible": eligible, "ineligibility_reasons": reasons,
            "saved": job_id in {s.job_id for s in user.saved_jobs}}


@app.post("/api/jobs/{job_id}/save", status_code=201)
def save_job(job_id: int, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    find_job(job_id)
    if not any(s.job_id == job_id for s in user.saved_jobs):
        db.add(models.SavedJob(user_id=user.id, job_id=job_id))
        db.commit()
    return {"saved": True, "job_id": job_id}


@app.delete("/api/jobs/{job_id}/save")
def unsave_job(job_id: int, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.query(models.SavedJob).filter_by(user_id=user.id, job_id=job_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Job is not saved")
    db.delete(row)
    db.commit()
    return {"saved": False, "job_id": job_id}


# ---------- skill gap, action plan, roadmap ----------
@app.post("/api/skills/gap-analysis")
def gap_analysis(body: GapIn, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    job = find_job(body.job_id)
    return {"job_id": job["id"], "job_title": job["title"],
            **skill_gap(effective_profile(user, db)["skills"], job)}


@app.get("/api/action-plan")
def action_plan(user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    r = latest_resume(db, user)
    failed = []
    if r:
        failed = [c for c in json.loads(r.ats_report or "{}").get("checks", []) if not c["passed"]]
    steps = build_action_plan(profile_out(user)["profile_completion"], r is not None, failed,
                              recommend(effective_profile(user, db), JOBS),
                              mock_history_rows(db, user), interview_history(db, user))
    return {"steps": steps}


@app.get("/api/roadmap")
def roadmap(user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    return build_roadmap(recommend(effective_profile(user, db), JOBS))


# ---------- AI status, mock test ----------
@app.get("/api/ai/status")
def ai_status():
    return {"ai_enabled": ai_enabled()}


@app.get("/api/mock-test/categories")
def get_categories():
    return mock_categories()


@app.get("/api/mock-test/questions")
def get_questions(category: str):
    if category not in MOCK_TESTS:
        raise HTTPException(status_code=404, detail="Unknown category")
    return prepare_mock(category)


@app.post("/api/mock-test/submit")
def submit_mock(body: MockSubmit, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    result = grade_mock(body.set_id, body.answers)
    if result is None:
        raise HTTPException(status_code=410, detail="This test has expired. Please start it again.")
    db.add(TestAttempt(user_id=user.id, category=result["category"], score=result["score"],
                       correct=result["correct"], total=result["total"]))
    db.commit()
    return result


@app.get("/api/mock-test/history")
def mock_history(user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    return mock_history_rows(db, user)


# ---------- mock interview ----------
@app.get("/api/interview/questions")
def interview_questions():
    return prepare_interview()


@app.post("/api/interview/evaluate")
def interview_evaluate(body: InterviewIn, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    try:
        result = evaluate_interview(body.set_id, body.question_id, body.answer)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown question")
    if result is None:
        raise HTTPException(status_code=410, detail="This interview session has expired. Please start again.")
    db.add(InterviewAttempt(user_id=user.id, question_id=body.question_id,
                            score=result["score"], feedback=result["feedback"]))
    db.commit()
    return result


@app.get("/api/interview/history")
def get_interview_history(user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    return interview_history(db, user)


# ---------- progress & readiness ----------
@app.get("/api/progress")
def progress(user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    prof = profile_out(user)["profile_completion"]
    r = latest_resume(db, user)
    ats = json.loads(r.ats_report or "{}").get("score", 0) if r else 0
    recs = recommend(effective_profile(user, db), JOBS)
    tests = mock_history_rows(db, user)
    ivs = interview_history(db, user)
    saved_count = len(user.saved_jobs)
    has_resume = r is not None
    steps = [
        {"key": "profile", "label": "Complete profile", "link": "profile", "done": prof >= 80},
        {"key": "resume", "label": "Upload resume", "link": "resume", "done": has_resume},
        {"key": "ats", "label": "Resume ATS score 60+", "link": "resume", "done": ats >= 60},
        {"key": "matches", "label": "Best career matches", "link": "matches",
         "done": bool(recs) and recs[0]["match_percentage"] >= 40},
        {"key": "gap", "label": "Skill gap analysis", "link": "gap", "done": has_resume},
        {"key": "plan", "label": "Personalized action plan", "link": "plan", "done": has_resume},
        {"key": "mock", "label": "Mock test", "link": "mock", "done": bool(tests)},
        {"key": "interview", "label": "Mock interview", "link": "interview", "done": bool(ivs)},
        {"key": "roadmap", "label": "Learning roadmap", "link": "roadmap", "done": has_resume},
        {"key": "jobs", "label": "Jobs and opportunities", "link": "jobs",
         "done": saved_count > 0 or any(j["eligible"] for j in recs)},
    ]
    return {
        "steps": steps,
        "completed": sum(1 for s in steps if s["done"]),
        "total": len(steps),
        "readiness": readiness(prof, ats, recs, tests, ivs),
    }


# ---------- simple web interface (http://localhost:8000) ----------
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
