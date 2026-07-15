@echo off
cd /d "%~dp0"

echo ========================================
echo Fix VENV Permission Issues
echo ========================================
echo.

echo Step 1: Kill any Python processes...
taskkill /f /im python.exe 2>nul
taskkill /f /im pythonw.exe 2>nul
echo OK

echo Step 2: Remove old venv...
rd /s /q "backend\venv" 2>nul
echo OK

echo Step 3: Create new venv...
python -m venv "backend\venv"
echo OK

echo Step 4: Install dependencies...
"backend\venv\Scripts\python.exe" -m pip install fastapi uvicorn sqlalchemy pydantic python-jose[cryptography] passlib python-multipart openpyxl python-dotenv pydantic-settings --quiet
echo OK

echo.
echo ========================================
echo VENV fixed successfully!
echo ========================================
pause
