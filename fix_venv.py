import os
import sys
import subprocess
import shutil

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")
VENV_DIR = os.path.join(BACKEND_DIR, "venv")


def run(cmd, cwd=None, shell=True):
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, cwd=cwd, shell=shell, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(f"STDERR: {result.stderr}")
    return result.returncode


print("=" * 50)
print("Fixing VENV Permission Issues")
print("=" * 50)
print()

print("Step 1: Kill Python processes...")
run("taskkill /f /im python.exe", shell=True)
run("taskkill /f /im pythonw.exe", shell=True)
print("Done")
print()

print("Step 2: Remove old venv...")
if os.path.exists(VENV_DIR):
    shutil.rmtree(VENV_DIR, ignore_errors=True)
    print("Done")
else:
    print("No existing venv")
print()

print("Step 3: Create new venv...")
code = run(f'{sys.executable} -m venv "{VENV_DIR}"')
if code == 0:
    print("Done")
else:
    print(f"Failed with code {code}")
    sys.exit(1)
print()

print("Step 4: Install dependencies...")
venv_python = os.path.join(VENV_DIR, "Scripts", "python.exe")
deps = "fastapi uvicorn sqlalchemy pydantic python-jose[cryptography] passlib python-multipart openpyxl python-dotenv pydantic-settings"
code = run(f'"{venv_python}" -m pip install {deps}')
if code == 0:
    print("Done")
else:
    print(f"Failed with code {code}")
    sys.exit(1)
print()

print("=" * 50)
print("VENV fixed successfully!")
print("=" * 50)
input("Press Enter to exit...")
