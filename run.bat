@echo off
title Smart Route AI - Final Year BCA Mini Project
color 0b

echo ==============================================================
echo        SMART ROUTE AI - FINAL YEAR BCA MINI PROJECT
echo ==============================================================
echo.
echo [1/3] Checking Python installation...
python --version
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH. Please install Python 3.
    pause
    exit /b
)

echo.
echo [2/3] Checking dependencies...
python -m pip install -r requirements.txt --quiet

echo.
echo [3/3] Launching Web Application...
start http://127.0.0.1:5000

echo.
echo Starting Flask Local Server on http://127.0.0.1:5000 ...
echo Press Ctrl + C to stop the server anytime.
echo.
python app.py

pause
