@echo off
echo ===================================================
echo    🎯 FACE ATTENDANCE SYSTEM (Simplified)  
echo ===================================================
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python not found. Please install Python 3.8+
    pause
    exit /b 1
)

echo ✅ Python found

REM Uninstall problematic packages
echo 📤 Cleaning up conflicting packages...
pip uninstall -y numpy opencv-python >nul 2>&1

REM Install specific compatible versions
echo 📦 Installing compatible packages...
pip install numpy==1.24.3
pip install opencv-python==4.10.0.84
pip install -r requirements.txt

echo ✅ Packages installed

REM Initialize database
echo 🗄️ Setting up database...
python models\database.py

echo ✅ Database ready

REM Create required directories
if not exist "uploads" mkdir uploads
if not exist "exports" mkdir exports
if not exist "static\img" mkdir static\img

echo ✅ Directories ready

echo.
echo 🚀 Starting application...
echo 📱 Access at: http://localhost:5000
echo 👤 Login: admin / admin123
echo.
echo ⚡ Press Ctrl+C to stop
echo ===================================================

python app_simple.py

pause
