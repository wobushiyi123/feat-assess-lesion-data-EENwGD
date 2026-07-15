@echo off
cd /d "%~dp0"

set "PYTHON=C:\Users\huawei\AppData\Local\Programs\Python\Python312\python.exe"
set "VENV=%~dp0venv"

echo ========================================
echo RECIST Backend Server
echo ========================================
echo.

echo [1/3] Checking virtual environment...
if not exist "%VENV%" (
    echo Creating virtual environment...
    "%PYTHON%" -m venv "%VENV%"
    echo OK: Created
)

echo [2/3] Installing dependencies...
"%VENV%\Scripts\python.exe" -m pip install -r "%~dp0requirements.txt" --quiet
echo OK

echo [3/3] Starting server...
echo.
echo URL: http://localhost:8080
echo Docs: http://localhost:8080/docs
echo.
"%VENV%\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8080

echo.
echo Server stopped.
pause