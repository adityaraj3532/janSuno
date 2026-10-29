@echo off
cd /d "%~dp0backend"
if not exist ".venv\Scripts\python.exe" py -m venv .venv
if not exist ".env" copy .env.example .env >nul
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (echo Dependency installation failed. & pause & exit /b 1)
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
pause
