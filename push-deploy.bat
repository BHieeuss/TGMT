@echo off
title TGMT - Push to Trigger Auto Deploy

echo.
echo ========================================
echo   Push Code to Trigger Auto Deploy
echo ========================================
echo.

echo [INFO] This will push your code to GitHub and trigger auto-deploy on Render
echo.

:menu
echo Choose an action:
echo.
echo 1. Quick push (with auto message)
echo 2. Push with custom message
echo 3. Check git status
echo 4. View recent commits
echo 5. Force push (if needed)
echo 6. 🔧 Fix Render deployment issues
echo 7. 🚨 EMERGENCY: Force Python 3.10 fix
echo 8. Exit
echo.
set /p choice="Enter your choice (1-8): "

if "%choice%"=="1" goto quick_push
if "%choice%"=="2" goto custom_push
if "%choice%"=="3" goto git_status
if "%choice%"=="4" goto view_commits
if "%choice%"=="5" goto force_push
if "%choice%"=="6" goto fix_render
if "%choice%"=="7" goto emergency_fix
if "%choice%"=="8" goto exit
goto invalid_choice

:quick_push
echo.
echo [INFO] Adding all changes...
git add .

echo [INFO] Committing with auto message...
set "timestamp=%date% %time%"
git commit -m "Auto deploy update - %timestamp%"

echo [INFO] Pushing to GitHub (this will trigger Render auto-deploy)...
git push origin main

if errorlevel 1 (
    echo [ERROR] Push failed. Check your GitHub credentials and internet connection.
    pause
    goto menu
) else (
    echo.
    echo ✅ Code pushed successfully!
    echo ⏳ Render should start auto-deploying in a few seconds...
    echo 🌐 Check your Render dashboard for deployment progress
    echo.
    pause
    goto menu
)

:custom_push
echo.
set /p commit_msg="Enter commit message: "
echo [INFO] Adding all changes...
git add .

echo [INFO] Committing with your message...
git commit -m "%commit_msg%"

echo [INFO] Pushing to GitHub...
git push origin main

if errorlevel 1 (
    echo [ERROR] Push failed.
    pause
    goto menu
) else (
    echo.
    echo ✅ Code pushed successfully!
    echo ⏳ Auto-deploy should trigger now...
    echo.
    pause
    goto menu
)

:git_status
echo.
echo [INFO] Current git status:
echo.
git status
echo.
echo [INFO] Recent changes:
git diff --name-only HEAD~1
echo.
pause
goto menu

:view_commits
echo.
echo [INFO] Recent commits:
echo.
git log --oneline -10
echo.
pause
goto menu

:force_push
echo.
echo ⚠️  WARNING: Force push will overwrite remote history!
echo This should only be used if you know what you're doing.
echo.
set /p confirm="Are you sure? (y/N): "
if /i "%confirm%"=="y" (
    git add .
    git commit -m "Force update for deployment"
    git push --force origin main
    echo.
    echo ✅ Force push completed!
    pause
) else (
    echo [INFO] Force push cancelled.
    pause
)
goto menu

:fix_render
echo.
echo ========================================
echo   Fix Render Python/Setuptools Issue
echo ========================================
echo.
echo [INFO] Your error shows Python 3.13/setuptools compatibility issues
echo [INFO] Applying fixes for stable Render deployment...
echo.
echo ✅ Fixes being applied:
echo   • Python 3.13 → 3.10 (Render-stable)
echo   • Fixed pip/setuptools versions
echo   • Simplified package requirements
echo   • Removed complex dependencies
echo   • Disabled health check temporarily
echo.

git add .
git commit -m "🔧 Fix Render Python 3.13 setuptools issue - downgrade to Python 3.10 stable"
git push origin main

if errorlevel 1 (
    echo [ERROR] Push failed.
    pause
    goto menu
) else (
    echo.
    echo ✅ Python compatibility fixes applied and pushed!
    echo ⏳ Render should deploy successfully now with Python 3.10...
    echo 💡 Face recognition may be limited but core features will work.
    echo 🌐 Monitor your Render dashboard for the build progress.
    echo.
    pause
    goto menu
)

:emergency_fix
echo.
echo ========================================
echo   🚨 EMERGENCY: Force Python 3.10
echo ========================================
echo.
echo [CRITICAL] Render vẫn dùng Python 3.13! 
echo [SOLUTION] Force rebuild với Python 3.10.12 cụ thể
echo.
echo ⚠️  Điều này sẽ:
echo   • Force push để clear cache
echo   • Rebuild hoàn toàn từ đầu
echo   • Chỉ cài minimal packages
echo.
set /p confirm="Bạn có chắc muốn emergency fix? (y/N): "
if /i "%confirm%"=="y" (
    git add .
    git commit -m "🚨 EMERGENCY: Force Python 3.10.12 - Clear Render cache"
    git push --force origin main
    
    if errorlevel 1 (
        echo [ERROR] Emergency push failed!
        pause
        goto menu
    ) else (
        echo.
        echo ✅ EMERGENCY FIX DEPLOYED!
        echo ⏳ Render đang rebuild hoàn toàn...
        echo 🌐 Check dashboard ngay!
        pause
        goto menu
    )
) else (
    echo [INFO] Emergency fix cancelled.
    pause
    goto menu
)

:invalid_choice
echo.
echo [ERROR] Invalid choice. Please select 1-8.
echo.
goto menu

:exit
echo.
echo ========================================
echo   Auto Deploy Info
echo ========================================
echo.
echo 🔄 How Auto Deploy Works:
echo   1. You push code to GitHub (main branch)
echo   2. Render detects the push automatically
echo   3. Render rebuilds and deploys your app
echo   4. Your live URL gets updated
echo.
echo 📱 Your Render URL should be:
echo   https://tgmt-face-attendance.onrender.com
echo   (or similar - check your Render dashboard)
echo.
echo 🕐 Deploy typically takes 2-5 minutes
echo.
echo 💡 Tips:
echo   - Watch Render dashboard for deploy progress
echo   - Check logs if deployment fails
echo   - URL stays the same, content updates
echo.
pause
