@echo off
setlocal enabledelayedexpansion

echo ==========================================================
echo    PDF CMYK Ink Coverage Analyzer - Setup and Launcher
echo ==========================================================
echo.

:: 1. Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Python is NOT installed on this machine.
    echo [INFO] Attempting to install Python 3.10 automatically via Windows Package Manager (winget)...
    echo.
    winget install --id Python.Python.3.10 --silent --accept-source-agreements --accept-package-agreements
    if !errorlevel! neq 0 (
        echo.
        echo [ERROR] Automatic installation via winget failed.
        echo Please install Python manually from: https://www.python.org/downloads/
        echo Make sure to check the box "Add Python to PATH" during installation.
        echo.
        pause
        exit /b 1
    )
    echo.
    echo [SUCCESS] Python has been successfully installed!
    echo.
    echo ==========================================================
    echo IMPORTANT: Please CLOSE this window and open/run this script 
    echo again to load Python into your system path.
    echo ==========================================================
    echo.
    pause
    exit /b 0
)

:: 2. Python is present, display version
for /f "tokens=*" %%i in ('python --version') do set pyver=%%i
echo [INFO] Detected %pyver%
echo.

:: 3. Create virtual environment if it doesn't exist
if not exist ".venv" (
    echo [INFO] Creating virtual environment (.venv)...
    python -m venv .venv
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

:: 4. Install dependencies
echo [INFO] Activating virtual environment and verifying dependencies...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo [SUCCESS] Setup complete! Launching the Streamlit dashboard...
echo.
streamlit run src/app.py

pause
