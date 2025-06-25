@echo off
echo ===================================================
echo    🎯 FACE RECOGNITION ATTENDANCE SYSTEM
echo ===================================================
echo.
echo 📋 Starting system initialization...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python 3.8+ and try again
    pause
    exit /b 1
)

echo ✅ Python found
echo.

REM Install dependencies
echo 📦 Installing required packages...
echo.
echo ⚠️  Uninstalling conflicting packages first...
pip uninstall -y numpy opencv-python face-recognition
echo.
echo 📥 Installing compatible versions...
pip install numpy==1.24.3
pip install opencv-python==4.10.0.84
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ❌ Failed to install packages
    pause
    exit /b 1
)

echo ✅ Packages installed successfully
echo.

REM Initialize database
echo 🗄️ Initializing database...
python models\database.py
if %errorlevel% neq 0 (
    echo ❌ Failed to initialize database
    pause
    exit /b 1
)

echo ✅ Database initialized successfully
echo.

REM Start the application
echo 🚀 Starting Flask application...
echo.
echo 📱 Access the application at: http://localhost:5000
echo 👤 Login credentials:
echo    Username: admin
echo    Password: admin123
echo.
echo 🎯 Features available:
echo    • Manage classes and students
echo    • Create attendance sessions  
echo    • Face recognition attendance
echo    • Generate Excel reports
echo.
echo ⚡ Press Ctrl+C to stop the server
echo ===================================================
echo.

python app.py

pause
