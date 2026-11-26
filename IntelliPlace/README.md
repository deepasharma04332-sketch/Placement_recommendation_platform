# IntelliPlace

A placement guidance web app: resume upload with ATS check, career matches,
skill gap analysis, action plan, mock tests, mock interviews, learning roadmap,
and placement progress.

## Quick start (Windows)

1. Double-click `setup.bat` (run it again after any update, because new libraries were added)
2. Double-click `run.bat` (the browser opens at http://localhost:8000)
3. Register, then follow the journey in the left sidebar:

   1. Dashboard
   2. Resume & ATS Check (upload PDF, DOCX or TXT)
   3. Best Career Matches
   4. Skill Gap Analysis
   5. Personalized Action Plan
   6. Mock Test
   7. Mock Interview
   8. Learning Roadmap
   9. Jobs & Opportunities
   10. Placement Progress (readiness score and Placement Success)

To run the tests, double-click `test.bat`.

## Mac / Linux

    ./setup.sh
    ./run.sh

## Optional: AI-generated questions (Gemini)
1. Get a free API key from Google AI Studio.
2. Open `backend/.env` in Notepad and set `GEMINI_API_KEY=your-key-here`.
3. Restart the app (close `run.bat` and open it again).

Without a key, mock tests and interviews use the built-in question bank.
If the AI call fails, the app falls back to the question bank automatically.

## Notes
- The ATS score is rule-based. It checks sections, contact details, keywords, action verbs and measurable results.
- Interview answers are scored by keyword matching. AI-generated questions also come with keywords.
- If an old `backend/intelliplace.db` causes problems, delete that file. The app creates a new one automatically. This removes existing accounts.
- API docs: http://localhost:8000/docs

## Planned next
A trained placement ML model (needs a dataset), AI feedback on interview answers,
PostgreSQL, and deployment.
