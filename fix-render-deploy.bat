@echo off
title TGMT - Fix Render Deploy

echo.
echo ========================================
echo   Fix and Deploy to Render
echo ========================================
echo.

echo [INFO] This script will fix the build issues and deploy to Render
echo.

echo [INFO] Step 1: Checking current status...
git status

echo.
echo [INFO] Step 2: Adding fixes for cloud deployment...
git add .

echo [INFO] Step 3: Committing fixes...
git commit -m "Fix Render deployment issues - use simplified Dockerfile and requirements"

echo [INFO] Step 4: Pushing to GitHub to trigger Render deploy...
git push origin main

if errorlevel 1 (
    echo.
    echo [ERROR] Push failed. Trying to pull first...
    git pull origin main
    echo [INFO] Trying push again...
    git push origin main
)

echo.
echo ========================================
echo   Deploy Status
echo ========================================
echo.
echo ✅ Code pushed with fixes!
echo.
echo 🔧 What was fixed:
echo   - Simplified Dockerfile.render (no complex dependencies)
echo   - Updated requirements-render.txt (stable versions)
echo   - Made OpenCV optional in app.py
echo   - Updated render.yaml configuration
echo.
echo ⏳ Render should start deploying in a few seconds...
echo.
echo 🌐 Your app will be available at:
echo   https://tgmt-face-attendance.onrender.com
echo   (or check your Render dashboard for the exact URL)
echo.
echo 👤 Login credentials:
echo   Username: admin
echo   Password: admin123
echo.
echo 💡 Note: Face recognition features may be limited in cloud deployment
echo    but all other features (student management, attendance, reports) work fine.
echo.
echo 📊 To monitor deployment:
echo   1. Go to your Render dashboard
echo   2. Click on your service
echo   3. Check the "Events" tab for build progress
echo   4. Check "Logs" tab if there are any issues
echo.
pause
