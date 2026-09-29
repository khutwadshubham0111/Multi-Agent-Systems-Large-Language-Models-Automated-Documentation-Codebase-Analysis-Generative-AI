@echo off
cd /d "%~dp0"

echo ==========================================
echo AI CODEBASE DOCUMENTATION GENERATOR
echo ==========================================
echo Starting system and opening browser...
echo.

call .venv\Scripts\activate

python main.py

pause