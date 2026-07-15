@echo off
cd /d "%~dp0"

set "BACKEND=%~dp0backend"
set "VENV=%BACKEND%\venv"

echo ========================================
echo RECIST Assessment System
echo ========================================
echo.

echo [1/5] Check Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.9+
    pause
    exit /b 1
)
echo OK

echo [2/5] Check Node.js...
where node >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js not found
    pause
    exit /b 1
)
echo OK

echo [3/5] Setup backend...
if not exist "%VENV%" (
    echo Creating virtual environment...
    python -m venv "%VENV%"
    echo Installing dependencies...
    "%VENV%\Scripts\python.exe" -m pip install fastapi uvicorn sqlalchemy pydantic python-jose[cryptography] "passlib[bcrypt]" "bcrypt<4.0.0" python-multipart openpyxl python-dotenv pydantic-settings --quiet
    echo OK
) else (
    echo OK: Venv already exists
)
echo OK

echo [4/5] Start backend server...
start "RECIST Backend (8080)" /d "%BACKEND%" "%VENV%\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8080
echo Waiting for backend...
timeout /t 5 /nobreak >nul
echo OK

echo [5/5] Start frontend server...
if not exist "node_modules" (
    echo Installing frontend dependencies...
    call npm install
    echo OK
)
start "RECIST Frontend (5173)" /d "%~dp0" npm run dev
echo OK

echo.
echo ========================================
echo Services started successfully!
echo ========================================
echo Frontend: http://localhost:5173
echo Backend:  http://localhost:8080
echo.
pause
