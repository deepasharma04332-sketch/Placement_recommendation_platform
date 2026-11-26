@echo off
title IntelliPlace - Setup
cd /d "%~dp0backend"
echo [1/3] Creating virtual environment...
if not exist .venv python -m venv .venv
call .venv\Scripts\activate
echo [2/3] Installing libraries (this can take 2-3 minutes)...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt
echo [3/3] Creating settings file...
if not exist .env copy .env.example .env >nul
echo.
echo =========================================
echo  SETUP COMPLETE! Now double-click run.bat
echo =========================================
pause
