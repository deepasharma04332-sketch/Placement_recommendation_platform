@echo off
title IntelliPlace - Server
cd /d "%~dp0backend"
if not exist .venv (
  echo Please run setup.bat first!
  pause
  exit /b 1
)
call .venv\Scripts\activate
echo Server is running. Open in browser: http://localhost:8000
echo Keep this window open. To stop the server, press CTRL+C.
start "" http://localhost:8000
uvicorn app.main:app --port 8000
pause
