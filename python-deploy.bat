@echo off
title TGMT - Python Standalone Deploy

echo.
echo ========================================
echo   TGMT Face Attendance - Python Deploy
echo ========================================
echo.

echo [INFO] This will run the application directly with Python
echo [INFO] No Docker required!
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed!
    echo Please install Python 3.8+ from: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo [INFO] Python found! Setting up environment...

:: Create virtual environment if it doesn't exist
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
)

:: Activate virtual environment
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

:: Install basic requirements only
echo [INFO] Installing basic requirements (this may take a few minutes)...
pip install Flask==2.3.3 Werkzeug==2.3.7 opencv-python-headless==4.10.0.84 numpy==1.24.3 Pillow==10.0.1 pandas==2.1.1 openpyxl==3.1.2 python-dateutil==2.8.2

if errorlevel 1 (
    echo [ERROR] Failed to install requirements
    echo [INFO] Trying alternative installation...
    pip install Flask Werkzeug opencv-python numpy Pillow pandas openpyxl python-dateutil
)

:: Get computer's IP address
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4 Address"') do (
    set "ip=%%a"
    goto :found_ip
)
:found_ip
set "ip=%ip: =%"

echo.
echo ========================================
echo   Starting Application...
echo ========================================
echo.
echo 🌐 Access URLs:
echo   - Local: http://localhost:5000
echo   - Network: http://%ip%:5000
echo.
echo 👤 Default Login:
echo   - Username: admin
echo   - Password: admin123
echo.
echo 📱 Share with others:
echo   Anyone on your network can access: http://%ip%:5000
echo.
echo ⚠️  Press Ctrl+C to stop the application
echo.

:: Set environment variables
set FLASK_ENV=development
set PYTHONPATH=%cd%

:: Start the application
echo [INFO] Starting Flask application...
python app.py
