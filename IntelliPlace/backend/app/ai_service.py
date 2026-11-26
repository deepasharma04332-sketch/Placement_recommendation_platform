"""Gemini integration for generating mock test and interview questions.

Every public function raises AIError on any problem, so callers can fall back
to the built-in question bank.
"""
import json
import re

import httpx

from .config import GEMINI_API_KEY, GEMINI_MODEL


class AIError(Exception):
    pass


def ai_enabled() -> bool:
    return bool(GEMINI_API_KEY)


def _parse_json(text: str):
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    return json.loads(cleaned)


def _call_gemini(prompt: str):
    if not ai_enabled():
        raise AIError("AI is not configured")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.8},
    }
    try:
        resp = httpx.post(url, params={"key": GEMINI_API_KEY}, json=body, timeout=25)
        resp.raise_for_status()
        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        return _parse_json(text)
    except Exception:
        # Do not include the exception text: it can contain the request URL with the key.
        raise AIError("AI request failed") from None


def validate_mcqs(data, n: int = 8) -> list[dict]:
    if not isinstance(data, list):
        raise AIError("Unexpected AI response shape")
    valid = []
    for item in data:
        try:
            question = str(item["question"]).strip()
            options = [str(o).strip() for o in item["options"]]
            answer = int(item["answer"])
        except (KeyError, TypeError, ValueError):
            continue
        if not question or len(options) != 4 or any(not o for o in options):
            continue
        if len({o.lower() for o in options}) != 4 or not 0 <= answer < 4:
            continue
        valid.append({"question": question, "options": options, "answer": answer})
    if len(valid) < 5:
        raise AIError("Not enough valid questions from AI")
    return valid[:n]


def validate_interview(data, n: int = 8) -> list[dict]:
    if not isinstance(data, list):
        raise AIError("Unexpected AI response shape")
    valid = []
    for item in data:
        try:
            question = str(item["question"]).strip()
            keywords = [str(k).strip().lower() for k in item["keywords"] if str(k).strip()]
            tip = str(item.get("tip", "")).strip() or "Give a clear, structured answer."
        except (KeyError, TypeError):
            continue
        if not question or len(keywords) < 2:
            continue
        valid.append({"question": question, "keywords": keywords[:6], "tip": tip})
    if len(valid) < 5:
        raise AIError("Not enough valid questions from AI")
    return valid[:n]


def generate_mcqs(topic: str, n: int = 8) -> list[dict]:
    prompt = (
        f"Create {n} unique multiple-choice questions for a placement test on: {topic}. "
        "Difficulty: beginner to intermediate, suitable for final-year students. "
        "Each question must have exactly 4 options, exactly one correct answer, and no duplicate options. "
        "Return ONLY a JSON array. Each item must be an object with keys: "
        '"question" (string), "options" (array of 4 strings), "answer" (integer 0 to 3, index of the correct option).'
    )
    return validate_mcqs(_call_gemini(prompt), n)


def generate_interview(n: int = 8) -> list[dict]:
    prompt = (
        f"Create {n} unique interview questions for a fresher applying for entry-level software and data jobs. "
        "Mix technical, problem-solving and HR questions. "
        "Return ONLY a JSON array. Each item must be an object with keys: "
        '"question" (string), "keywords" (array of 3 to 5 lowercase words or short phrases that a good answer should mention), '
        '"tip" (one short sentence of advice for answering).'
    )
    return validate_interview(_call_gemini(prompt), n)
