@echo off
title TGMT - Cloud Deployment

echo.
echo ========================================
echo   TGMT - Deploy to Cloud (24/7)
echo ========================================
echo.
echo Choose a cloud platform to deploy:
echo (Your app will run 24/7 even when your computer is off)
echo.

:menu
echo.
echo 1. 🚀 Render.com (Recommended - Free, Easy)
echo 2. 🚄 Railway.app (Fast deployment)
echo 3. 📱 Vercel (Good for demos)
echo 4. 🔧 Heroku (Professional)
echo 5. 🐳 Deploy to DockerHub (for advanced users)
echo 6. ℹ️  Show deployment status
echo 7. 📋 Copy deployment files
echo 8. Exit
echo.
set /p choice="Enter your choice (1-8): "

if "%choice%"=="1" goto render_deploy
if "%choice%"=="2" goto railway_deploy
if "%choice%"=="3" goto vercel_deploy
if "%choice%"=="4" goto heroku_deploy
if "%choice%"=="5" goto dockerhub_deploy
if "%choice%"=="6" goto deployment_status
if "%choice%"=="7" goto copy_files
if "%choice%"=="8" goto exit
goto invalid_choice

:render_deploy
echo.
echo ========================================
echo   Render.com Deployment
echo ========================================
echo.
echo [INFO] Render.com is the easiest way to deploy!
echo.
echo Step 1: Push your code to GitHub
git status
echo.
echo [INFO] Checking if code is committed...
git add .
git commit -m "Add cloud deployment support"
git push origin main
if errorlevel 1 (
    echo [WARNING] Make sure your code is on GitHub first
)
echo.
echo Step 2: Deploy on Render
echo.
echo 1. Go to: https://render.com/
echo 2. Sign up with GitHub account
echo 3. Click "New" → "Web Service"
echo 4. Connect repository: BHieeuss/TGMT
echo 5. Settings:
echo    - Name: tgmt-face-attendance
echo    - Environment: Docker
echo    - Dockerfile path: Dockerfile.cloud
echo    - Region: Singapore
echo 6. Click "Create Web Service"
echo.
echo ✅ Your app will be available at:
echo    https://tgmt-face-attendance.onrender.com
echo.
echo 📱 Share this URL with anyone!
echo 👤 Login: admin / admin123
echo.
pause
goto menu

:railway_deploy
echo.
echo ========================================
echo   Railway.app Deployment
echo ========================================
echo.
echo [INFO] Railway is super fast and easy!
echo.
echo Step 1: Ensure code is on GitHub
git add .
git commit -m "Add railway deployment"
git push origin main
echo.
echo Step 2: Deploy on Railway
echo.
echo 1. Go to: https://railway.app/
echo 2. Login with GitHub
echo 3. Click "Deploy from GitHub repo"
echo 4. Select: BHieeuss/TGMT
echo 5. Railway will auto-detect and deploy!
echo.
echo ✅ Your app will be available at:
echo    https://your-app.railway.app
echo.
pause
goto menu

:vercel_deploy
echo.
echo ========================================
echo   Vercel Deployment
echo ========================================
echo.
echo [INFO] Vercel is great for quick demos!
echo.
echo Step 1: Push to GitHub
git add .
git commit -m "Add vercel deployment"
git push origin main
echo.
echo Step 2: Deploy on Vercel
echo.
echo 1. Go to: https://vercel.com/
echo 2. Import Git Repository
echo 3. Select: BHieeuss/TGMT
echo 4. Click "Deploy"
echo.
echo ✅ Your app will be available at:
echo    https://tgmt-face-attendance.vercel.app
echo.
pause
goto menu

:heroku_deploy
echo.
echo ========================================
echo   Heroku Deployment
echo ========================================
echo.
echo [INFO] Heroku is professional but requires setup
echo.
echo Step 1: Install Heroku CLI
echo Download from: https://devcenter.heroku.com/articles/heroku-cli
echo.
echo Step 2: Deploy
echo.
echo Run these commands:
echo.
echo heroku login
echo heroku create tgmt-face-attendance
echo git push heroku main
echo.
echo ✅ Your app will be available at:
echo    https://tgmt-face-attendance.herokuapp.com
echo.
pause
goto menu

:dockerhub_deploy
echo.
echo ========================================
echo   DockerHub Deployment
echo ========================================
echo.
echo [INFO] This creates a Docker image others can run anywhere
echo.
echo Step 1: Build and push to DockerHub
echo.
echo docker build -f Dockerfile.cloud -t your-username/tgmt-face-attendance .
echo docker push your-username/tgmt-face-attendance
echo.
echo Step 2: Others can run with:
echo docker run -p 5000:5000 your-username/tgmt-face-attendance
echo.
echo Step 3: Deploy to cloud services using this image
echo.
pause
goto menu

:deployment_status
echo.
echo ========================================
echo   Deployment Status Check
echo ========================================
echo.
echo Checking common deployment URLs...
echo.

:: Check Render
echo [INFO] Checking Render deployment...
curl -s -o nul -w "%%{http_code}" https://tgmt-face-attendance.onrender.com/health
if not errorlevel 1 (
    echo ✅ Render: https://tgmt-face-attendance.onrender.com
) else (
    echo ❌ Render: Not deployed or not responding
)

:: Check Railway
echo [INFO] Checking Railway deployment...
echo ⚠️  Railway URL varies - check your Railway dashboard

:: Check Vercel
echo [INFO] Checking Vercel deployment...
curl -s -o nul -w "%%{http_code}" https://tgmt-face-attendance.vercel.app/health
if not errorlevel 1 (
    echo ✅ Vercel: https://tgmt-face-attendance.vercel.app
) else (
    echo ❌ Vercel: Not deployed or not responding
)

echo.
echo 📱 If any URL works, share it with others!
echo 👤 Login: admin / admin123
echo.
pause
goto menu

:copy_files
echo.
echo ========================================
echo   Deployment Files Created
echo ========================================
echo.
echo The following files have been created for cloud deployment:
echo.
echo ✅ Dockerfile.cloud - Optimized for cloud
echo ✅ requirements-cloud.txt - Cloud dependencies  
echo ✅ Procfile - For Heroku
echo ✅ render.yaml - For Render.com
echo ✅ railway.toml - For Railway.app
echo ✅ vercel.json - For Vercel
echo ✅ docker-compose.cloud.yml - Cloud Docker Compose
echo.
echo 📋 All files are ready for deployment!
echo.
pause
goto menu

:invalid_choice
echo.
echo [ERROR] Invalid choice. Please select 1-8.
echo.
goto menu

:exit
echo.
echo ========================================
echo   Cloud Deployment Summary
echo ========================================
echo.
echo 🥇 Easiest: Render.com
echo    - Sign up with GitHub
echo    - One-click deploy
echo    - Free tier available
echo.
echo 🥈 Fastest: Railway.app  
echo    - Auto-detection
echo    - Simple interface
echo.
echo 🥉 Good for demos: Vercel
echo    - Great for sharing
echo    - Fast builds
echo.
echo 📊 After deployment:
echo ✅ Your app runs 24/7
echo ✅ No need to keep computer on
echo ✅ Anyone can access via URL
echo ✅ Auto-updates when you push code
echo.
echo 🔗 Share the URL with:
echo    Username: admin
echo    Password: admin123
echo.
echo 💡 Remember to change default password for security!
echo.
pause
