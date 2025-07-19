@echo off
title TGMT - Internet Access Setup

echo.
echo ========================================
echo   TGMT - Setup Internet Access
echo ========================================
echo.
echo This script helps you share your Face Attendance app
echo with people on different networks (via internet)
echo.

:menu
echo Choose a method to share your app:
echo.
echo 1. Setup Ngrok (Recommended - Free)
echo 2. Setup LocalTunnel (Simple)
echo 3. Show Port Forwarding guide
echo 4. Check if app is running
echo 5. Exit
echo.
set /p choice="Enter your choice (1-5): "

if "%choice%"=="1" goto setup_ngrok
if "%choice%"=="2" goto setup_localtunnel
if "%choice%"=="3" goto port_forwarding_guide
if "%choice%"=="4" goto check_app
if "%choice%"=="5" goto exit
goto invalid_choice

:setup_ngrok
echo.
echo [INFO] Setting up Ngrok for internet access...
echo.

:: Check if ngrok exists
ngrok version >nul 2>&1
if errorlevel 1 (
    echo [INFO] Ngrok not found. Let's download it...
    echo.
    echo Please follow these steps:
    echo 1. Go to: https://ngrok.com/download
    echo 2. Download ngrok for Windows
    echo 3. Extract ngrok.exe to this folder
    echo 4. Create free account at: https://ngrok.com/signup
    echo 5. Get your authtoken from dashboard
    echo 6. Run this script again
    echo.
    pause
    goto menu
)

echo [INFO] Ngrok found! Checking authentication...

:: Check if app is running
netstat -an | findstr ":5000" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] App is not running on port 5000!
    echo [INFO] Please start your app first:
    echo   - Run: python-deploy.bat
    echo   - Or: simple-deploy.bat
    echo.
    pause
    goto menu
)

echo [INFO] App is running on port 5000 ✅
echo.
echo [INFO] Creating public tunnel...
echo.
echo ⚠️  Keep this window open while sharing your app!
echo 📱 The tunnel URL will be displayed below:
echo.

:: Start ngrok
ngrok http 5000

goto menu

:setup_localtunnel
echo.
echo [INFO] Setting up LocalTunnel...
echo.

:: Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is not installed!
    echo Please install Node.js from: https://nodejs.org/
    pause
    goto menu
)

:: Check if app is running
netstat -an | findstr ":5000" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] App is not running on port 5000!
    echo Please start your app first.
    pause
    goto menu
)

echo [INFO] Installing LocalTunnel...
npm install -g localtunnel

echo.
echo [INFO] Creating tunnel...
echo ⚠️  Keep this window open while sharing your app!
echo.

:: Start localtunnel
lt --port 5000 --subdomain tgmt-attendance

goto menu

:port_forwarding_guide
echo.
echo ========================================
echo   Port Forwarding Guide
echo ========================================
echo.
echo This method requires router configuration:
echo.
echo Step 1: Find your internal IP
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4 Address"') do (
    set "internal_ip=%%a"
    goto :found_internal_ip
)
:found_internal_ip
set "internal_ip=%internal_ip: =%"
echo   Your internal IP: %internal_ip%
echo.
echo Step 2: Find your public IP
echo   Go to: https://whatismyipaddress.com/
echo   Note down your public IP address
echo.
echo Step 3: Configure your router
echo   1. Open router admin (usually 192.168.1.1 or 192.168.0.1)
echo   2. Find "Port Forwarding" or "Virtual Server"
echo   3. Add new rule:
echo      - External Port: 8080
echo      - Internal IP: %internal_ip%
echo      - Internal Port: 5000
echo      - Protocol: TCP
echo   4. Save and restart router
echo.
echo Step 4: Share with others
echo   Your public URL: http://[YOUR_PUBLIC_IP]:8080
echo   Username: admin
echo   Password: admin123
echo.
echo ⚠️  Security warning:
echo   - Change default password
echo   - Only share with trusted people
echo   - Consider using firewall rules
echo.
pause
goto menu

:check_app
echo.
echo [INFO] Checking if Face Attendance app is running...
echo.

:: Check port 5000
netstat -an | findstr ":5000" >nul 2>&1
if errorlevel 1 (
    echo ❌ App is NOT running on port 5000
    echo.
    echo To start the app, run one of these:
    echo   - python-deploy.bat
    echo   - simple-deploy.bat
    echo   - quick-deploy.bat
) else (
    echo ✅ App is running on port 5000
    
    :: Test health endpoint
    curl -s http://localhost:5000/health >nul 2>&1
    if errorlevel 1 (
        echo ⚠️  App is running but may not be responding properly
    ) else (
        echo ✅ App is healthy and ready to share!
    )
)

echo.
echo Local access: http://localhost:5000
echo.
pause
goto menu

:invalid_choice
echo.
echo [ERROR] Invalid choice. Please select 1-5.
echo.
goto menu

:exit
echo.
echo ========================================
echo   Quick Reference
echo ========================================
echo.
echo To share your app with people on different networks:
echo.
echo 🥇 Best: Ngrok (option 1)
echo   - Free, secure, easy to use
echo   - Creates https:// URLs
echo   - No router configuration needed
echo.
echo 🥈 Alternative: LocalTunnel (option 2)  
echo   - Free, simple
echo   - Requires Node.js
echo.
echo 🥉 Advanced: Port Forwarding (option 3)
echo   - Requires router access
echo   - Permanent solution
echo   - More complex setup
echo.
echo Remember to:
echo ✅ Start your app first
echo ✅ Keep tunnel window open
echo ✅ Share login: admin/admin123
echo ✅ Change default password for security
echo.
echo Goodbye!
pause
