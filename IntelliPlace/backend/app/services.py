"""Business logic: mock tests and interviews (AI with question-bank fallback), roadmap, plan, readiness."""
import random
from collections import Counter

from . import session_store
from .ai_service import AIError, ai_enabled, generate_interview, generate_mcqs
from .content import INTERVIEW_QUESTIONS, MOCK_TESTS

FALLBACK_NOTE = "AI questions are unavailable right now, so this set comes from the question bank."


def mock_categories() -> list[dict]:
    return [{"id": cid, "name": name, "questions": len(qs)} for cid, (name, qs) in MOCK_TESTS.items()]


def _shuffle_mcq(question: str, options: list[str], answer: int) -> dict:
    correct_text = options[answer]
    shuffled = list(options)
    random.shuffle(shuffled)
    return {"question": question, "options": shuffled, "answer": shuffled.index(correct_text)}


def prepare_mock(category: str) -> dict:
    name, bank = MOCK_TESTS[category]
    source, note, items = "bank", "", None
    if ai_enabled():
        try:
            items = [_shuffle_mcq(i["question"], i["options"], i["answer"]) for i in generate_mcqs(name)]
            source = "ai"
        except AIError:
            note = FALLBACK_NOTE
    if items is None:
        picked = random.sample(bank, min(8, len(bank)))
        items = [_shuffle_mcq(q, opts, ans) for q, opts, ans in picked]
    set_id = session_store.put("mock", {"category": category, "name": name}, items)
    return {"set_id": set_id, "source": source, "note": note,
            "questions": [{"id": i, "question": x["question"], "options": x["options"]} for i, x in enumerate(items)]}


def grade_mock(set_id: str, answers: dict[str, int]):
    entry = session_store.get(set_id, "mock")
    if entry is None:
        return None
    items = entry["items"]
    correct, review = 0, []
    for i, x in enumerate(items):
        chosen = answers.get(str(i))
        ok = chosen == x["answer"]
        correct += int(ok)
        review.append({
            "question": x["question"],
            "options": x["options"],
            "your_answer": x["options"][chosen] if chosen is not None and 0 <= chosen < len(x["options"]) else "Not answered",
            "correct_answer": x["options"][x["answer"]],
            "is_correct": ok,
        })
    total = len(items)
    return {"category": entry["meta"]["category"], "name": entry["meta"]["name"],
            "correct": correct, "total": total,
            "score": round(100 * correct / total, 1) if total else 0.0, "review": review}


def prepare_interview() -> dict:
    source, note, items = "bank", "", None
    if ai_enabled():
        try:
            items = generate_interview()
            source = "ai"
        except AIError:
            note = FALLBACK_NOTE
    if items is None:
        picked = random.sample(INTERVIEW_QUESTIONS, min(8, len(INTERVIEW_QUESTIONS)))
        items = [{"question": q, "keywords": [k.lower() for k in kws], "tip": tip} for q, kws, tip in picked]
    set_id = session_store.put("interview", {}, items)
    return {"set_id": set_id, "source": source, "note": note,
            "questions": [{"id": i, "question": x["question"]} for i, x in enumerate(items)]}


def evaluate_interview(set_id: str, question_id: int, answer: str):
    """Returns None if the session expired. Raises KeyError for an unknown question."""
    entry = session_store.get(set_id, "interview")
    if entry is None:
        return None
    items = entry["items"]
    if not 0 <= question_id < len(items):
        raise KeyError("Invalid question")
    item = items[question_id]
    text = answer.lower()
    found = [k for k in item["keywords"] if k in text]
    required = min(3, len(item["keywords"])) or 1
    score = min(100.0, round(100 * len(found) / required, 1))
    feedback = []
    if len(answer.split()) < 15:
        score = min(score, 60.0)
        feedback.append("Your answer is short. Explain in 3 to 5 sentences.")
    if found:
        feedback.append("Good points: " + ", ".join(found) + ".")
    if score < 100:
        feedback.append("Tip: " + item["tip"])
    return {"question": item["question"], "score": score, "found": found, "feedback": " ".join(feedback)}


def build_roadmap(recs: list[dict]) -> dict:
    counts = Counter()
    for r in recs[:5]:
        counts.update(r["missing_skills"])
    if not counts:
        return {"weeks": [], "message": "You already have the skills for your top matches. Focus on mock tests and interview practice."}
    weeks, week = [], 1
    for skill, n in counts.most_common(8):
        weeks.append({
            "weeks": f"{week}-{week + 1}",
            "focus": skill,
            "why": f"Required by {n} of your top 5 matches",
            "tasks": [f"Learn the core concepts of {skill}",
                      f"Practice {skill} with 10 small exercises",
                      f"Build one small project using {skill}"],
        })
        week += 2
    return {"weeks": weeks, "message": ""}


def build_action_plan(profile_completion: float, has_resume: bool, failed_checks: list[dict],
                      recs: list[dict], tests: list, interviews: list) -> list[dict]:
    steps = []
    if profile_completion < 100:
        steps.append({"priority": "High", "title": "Complete your profile",
                      "detail": f"Your profile is {round(profile_completion)}% complete. Fill in CGPA, skills and interests.",
                      "link": "profile"})
    if not has_resume:
        steps.append({"priority": "High", "title": "Upload your resume",
                      "detail": "We need your resume to check ATS score and detect your skills.",
                      "link": "resume"})
    for c in sorted(failed_checks, key=lambda c: -c["max"])[:3]:
        steps.append({"priority": "Medium", "title": "Resume: " + c["name"], "detail": c["tip"], "link": "resume"})
    top_missing = Counter()
    for r in recs[:3]:
        top_missing.update(r["missing_skills"])
    if top_missing:
        skills = [s for s, _ in top_missing.most_common(3)]
        steps.append({"priority": "High", "title": "Learn: " + ", ".join(skills),
                      "detail": "These skills appear in your best matches. Follow the learning roadmap.",
                      "link": "roadmap"})
    if not tests:
        steps.append({"priority": "Medium", "title": "Take a mock test",
                      "detail": "Check your Python, SQL and aptitude level.", "link": "mock"})
    else:
        by_cat = {}
        for t in tests:
            by_cat.setdefault(t["category"], []).append(t["score"])
        weakest = min(by_cat.items(), key=lambda kv: sum(kv[1]) / len(kv[1]))
        avg = sum(weakest[1]) / len(weakest[1])
        if avg < 60:
            steps.append({"priority": "Medium", "title": f"Revise {MOCK_TESTS[weakest[0]][0]}",
                          "detail": f"Your average in this category is {round(avg)}%. Practice more and retake the test.",
                          "link": "mock"})
    if not interviews:
        steps.append({"priority": "Medium", "title": "Practice mock interview",
                      "detail": "Answer a few common interview questions and get feedback.", "link": "interview"})
    eligible_top = [r for r in recs if r["eligible"]][:3]
    if eligible_top:
        steps.append({"priority": "High", "title": "Apply to your top eligible jobs",
                      "detail": ", ".join(f"{r['title']} ({r['match_percentage']}%)" for r in eligible_top),
                      "link": "jobs"})
    else:
        steps.append({"priority": "Medium", "title": "Check eligibility reasons",
                      "detail": "No job fits your current CGPA, branch or backlogs. Open a job to see the reasons.",
                      "link": "jobs"})
    return steps


def readiness(profile_completion: float, ats_score: float, recs: list[dict], tests: list, interviews: list) -> dict:
    top = [r["match_percentage"] for r in recs[:3]]
    top_avg = sum(top) / len(top) if top else 0.0
    mock_avg = sum(t["score"] for t in tests) / len(tests) if tests else 0.0
    iv_avg = sum(i["score"] for i in interviews) / len(interviews) if interviews else 0.0
    components = [
        {"name": "Profile completion", "value": round(profile_completion, 1), "weight": 20},
        {"name": "Resume ATS score", "value": round(ats_score, 1), "weight": 20},
        {"name": "Best match average", "value": round(top_avg, 1), "weight": 20},
        {"name": "Mock test average", "value": round(mock_avg, 1), "weight": 20},
        {"name": "Interview average", "value": round(iv_avg, 1), "weight": 20},
    ]
    score = round(sum(c["value"] * c["weight"] for c in components) / 100, 1)
    if score >= 75:
        label = "Placement Success: you are ready to apply"
    elif score >= 50:
        label = "On track: keep improving the weak areas"
    else:
        label = "Keep building: follow your action plan"
    return {"score": score, "label": label, "components": components}
