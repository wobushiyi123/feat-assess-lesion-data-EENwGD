@echo off
cd /d "%~dp0"
set "VENV=%~dp0venv"

echo Starting RECIST Backend...
echo.
"%VENV%\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8080
pause