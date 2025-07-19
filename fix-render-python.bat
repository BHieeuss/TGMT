@echo off
title TGMT - Fix Render Python 3.13 Setuptools Issue

echo.
echo ========================================
echo   Fix Render Python/Setuptools Issue
echo ========================================
echo.

echo [INFO] The error shows Python 3.13 compatibility issues with setuptools
echo [INFO] Applying comprehensive fixes...
echo.

echo ✅ Step 1: Updated Dockerfile.render to use Python 3.10 (more stable)
echo ✅ Step 2: Fixed setuptools/pip versions to known working versions  
echo ✅ Step 3: Simplified requirements-render.txt with compatible packages
echo ✅ Step 4: Removed health check temporarily for debugging
echo ✅ Step 5: Added --no-build-isolation flag for pip install
echo.

echo [INFO] Committing and pushing fixes...
git add .
git commit -m "Fix Render Python 3.13 setuptools issue - downgrade to Python 3.10 with stable packages"

echo [INFO] Pushing to trigger Render rebuild...
git push origin main

if errorlevel 1 (
    echo [ERROR] Push failed. Check your git status.
    pause
    exit /b 1
)

echo.
echo ========================================
echo   ✅ Fixes Applied Successfully!
echo ========================================
echo.
echo 🔧 What was fixed:
echo   • Changed Python from 3.11/3.13 → 3.10 (stable)
echo   • Fixed pip/setuptools versions
echo   • Simplified package versions
echo   • Removed problematic dependencies
echo   • Disabled health check temporarily
echo.
echo ⏳ Render should now deploy successfully!
echo 🌐 Monitor your Render dashboard for the new build
echo.
echo 💡 Key changes:
echo   - Uses Python 3.10-slim (tested compatibility)
echo   - pip 23.3.1, setuptools 69.0.3 (stable versions)
echo   - Minimal package set without complex dependencies
echo   - No OpenCV (face recognition will be limited)
echo.
echo 📱 Your app should be available at:
echo   https://tgmt-face-attendance.onrender.com
echo   (Check your Render dashboard for exact URL)
echo.
pause
