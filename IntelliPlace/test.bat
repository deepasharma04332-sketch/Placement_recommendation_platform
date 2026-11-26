@echo off
title IntelliPlace - Tests
cd /d "%~dp0backend"
if not exist .venv (
  echo Please run setup.bat first!
  pause
  exit /b 1
)
call .venv\Scripts\activate
pytest -v
pause
