"""Resume parsing, skill detection and a rule-based ATS check."""
import io
import re
from collections import OrderedDict

from .content import ACTION_VERBS, SKILL_DICTIONARY

ALLOWED_EXTENSIONS = (".pdf", ".docx", ".txt")
MAX_BYTES = 5 * 1024 * 1024

_SKILL_PATTERNS = [
    (skill, re.compile(r"(?<![A-Za-z0-9+#.])" + re.escape(skill) + r"(?![A-Za-z0-9+#])", re.IGNORECASE))
    for skill in SKILL_DICTIONARY
]
_VERB_PATTERNS = [(v, re.compile(r"\b" + v + r"\b", re.IGNORECASE)) for v in ACTION_VERBS]
_DEGREE = re.compile(r"\b(B\.?\s?Tech|B\.?E\.?|BCA|MCA|B\.?Sc|M\.?Sc|M\.?Tech|MBA|Bachelor[^\n,]{0,40}|Master[^\n,]{0,40}|Diploma|Ph\.?D)\b", re.IGNORECASE)


class ResumeError(ValueError):
    pass


def extract_text(filename: str, data: bytes) -> str:
    name = (filename or "").lower()
    ext = next((e for e in ALLOWED_EXTENSIONS if name.endswith(e)), None)
    if ext is None:
        raise ResumeError("Only PDF, DOCX or TXT files are allowed.")
    if not data:
        raise ResumeError("The file is empty.")
    if len(data) > MAX_BYTES:
        raise ResumeError("The file is larger than 5 MB.")

    if ext == ".txt":
        text = data.decode("utf-8", errors="ignore")
    elif ext == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            raise ResumeError("PDF support is not installed. Run setup.bat again.")
        try:
            reader = PdfReader(io.BytesIO(data))
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception:
            raise ResumeError("Could not read this PDF. Try a DOCX or TXT file.")
    else:
        try:
            from docx import Document
        except ImportError:
            raise ResumeError("DOCX support is not installed. Run setup.bat again.")
        try:
            doc = Document(io.BytesIO(data))
            text = "\n".join(p.text for p in doc.paragraphs)
        except Exception:
            raise ResumeError("Could not read this DOCX file.")

    text = text.strip()
    if len(text) < 30:
        raise ResumeError("Not enough text found in this file. Scanned PDFs do not work; use a text-based PDF, DOCX or TXT.")
    return text


def detect_skills(text: str) -> list[str]:
    return [skill for skill, pattern in _SKILL_PATTERNS if pattern.search(text)]


def detect_info(text: str) -> dict:
    email = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text)
    phone = re.search(r"(\+?\d[\d\s-]{8,14}\d)", text)
    degrees = list(OrderedDict.fromkeys(m.group(0).strip() for m in _DEGREE.finditer(text)))
    name = None
    for line in text.splitlines():
        line = line.strip()
        if line and 2 <= len(line.split()) <= 4 and len(line) < 40 and not re.search(r"[\d@:/]", line):
            name = line
            break
    lower = text.lower()
    return {
        "name": name,
        "email": email.group(0) if email else None,
        "phone": phone.group(0).strip() if phone else None,
        "education": degrees[:3],
        "has_linkedin": "linkedin.com" in lower,
        "has_github": "github.com" in lower,
    }


def analyze_ats(text: str, skills: list[str]) -> dict:
    info = detect_info(text)
    words = len(text.split())
    lower = text.lower()
    verbs_used = [v for v, p in _VERB_PATTERNS if p.search(text)]
    numeric_lines = sum(1 for line in text.splitlines() if re.search(r"\d", line))

    def has_section(*words_):
        return any(re.search(r"\b" + w + r"\b", lower) for w in words_)

    checks = [
        {"name": "Email address", "max": 6, "passed": bool(info["email"]),
         "tip": "Add a professional email address near the top."},
        {"name": "Phone number", "max": 6, "passed": bool(info["phone"]),
         "tip": "Add a phone number so recruiters can reach you."},
        {"name": "LinkedIn or GitHub link", "max": 6, "passed": info["has_linkedin"] or info["has_github"],
         "tip": "Add your LinkedIn and GitHub profile links."},
        {"name": "Summary or objective", "max": 6, "passed": has_section("summary", "objective", "profile"),
         "tip": "Add a 2 to 3 line summary about your goal and strengths."},
        {"name": "Education section", "max": 10, "passed": has_section("education", "academic"),
         "tip": "Add an Education section with degree, college and year."},
        {"name": "Experience or internship", "max": 10, "passed": has_section("experience", "internship", "work history"),
         "tip": "Add internships, freelance work or part-time jobs. Even small ones help."},
        {"name": "Projects section", "max": 10, "passed": has_section("projects", "project"),
         "tip": "Add 2 to 3 projects with the tech used and what they do."},
        {"name": "Skills section", "max": 6, "passed": has_section("skills", "technical skills"),
         "tip": "Add a clear Skills section with a list of technologies."},
        {"name": "Enough keywords (8 or more skills)", "max": 10, "passed": len(skills) >= 8,
         "tip": "Mention more relevant technologies and tools that match job descriptions."},
        {"name": "Certifications or achievements", "max": 6, "passed": has_section("certification", "certifications", "achievements", "awards"),
         "tip": "Add certifications, courses or achievements."},
        {"name": "Action verbs (5 or more)", "max": 8, "passed": len(verbs_used) >= 5,
         "tip": "Start bullet points with action verbs like built, developed, improved, led."},
        {"name": "Measurable results (3 or more lines with numbers)", "max": 10, "passed": numeric_lines >= 3,
         "tip": "Add numbers to show impact, such as 'improved speed by 30%' or 'handled 500 records'."},
        {"name": "Good length (250 to 900 words)", "max": 6, "passed": 250 <= words <= 900,
         "tip": "Keep the resume to one or two pages, about 250 to 900 words."},
    ]
    earned = sum(c["max"] for c in checks if c["passed"])
    total = sum(c["max"] for c in checks)
    return {
        "score": round(100 * earned / total, 1),
        "checks": checks,
        "word_count": words,
        "action_verbs_found": verbs_used,
        "info": info,
    }
