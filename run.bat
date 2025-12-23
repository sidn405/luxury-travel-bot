@echo off
REM Luxury Travel Bot - Local Run Script for Windows
REM This script runs the bot locally for testing

echo ======================================
echo Luxury Travel Bot - Starting...
echo ======================================
echo.

REM Check if virtual environment exists
if not exist "venv\" (
    echo Error: Virtual environment not found!
    echo Please run setup.ps1 first
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Check if .env file exists
if not exist ".env" (
    echo Warning: .env file not found!
    echo Please create .env file with your OPENAI_API_KEY
    echo You can copy .env.example to .env
    pause
    exit /b 1
)

REM Load environment variables from .env
for /f "tokens=*" %%a in (.env) do (
    set %%a
)

REM Set default PORT if not set
if not defined PORT set PORT=8080

echo.
echo Starting bot on http://localhost:%PORT%
echo Press Ctrl+C to stop
echo.

REM Run the bot with Python directly (not gunicorn on Windows)
python Luxury_Travel_Bot.py

pause