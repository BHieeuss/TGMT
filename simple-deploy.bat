@echo off
title TGMT - Simple Deploy

echo.
echo ========================================
echo   TGMT Face Attendance - Simple Deploy
echo ========================================
echo.

echo [INFO] This script will deploy a simplified version without complex dependencies
echo [INFO] Perfect for quick testing and demos
echo.

:: Stop any existing containers
echo [INFO] Stopping existing containers...
docker-compose -f docker-compose.simple.yml down >nul 2>&1

:: Build and start
echo [INFO] Building and starting simplified application...
docker-compose -f docker-compose.simple.yml up --build -d

echo.
echo [INFO] Waiting for application to start...
timeout /t 20 /nobreak >nul

:: Get computer's IP address
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4 Address"') do (
    set "ip=%%a"
    goto :found_ip
)
:found_ip
set "ip=%ip: =%"

echo.
echo ========================================
echo   Deployment Complete!
echo ========================================
echo.
echo 🌐 Access URLs:
echo   - Local: http://localhost:5000
echo   - Local Alt: http://localhost
echo   - Network: http://%ip%:5000
echo   - Network Alt: http://%ip%
echo.
echo 👤 Default Login:
echo   - Username: admin
echo   - Password: admin123
echo.
echo 📱 Share with others:
echo   Anyone on your network can access: http://%ip%:5000
echo.
echo 🛠️ Management:
echo   - View logs: docker-compose -f docker-compose.simple.yml logs -f
echo   - Stop: docker-compose -f docker-compose.simple.yml down
echo   - Restart: docker-compose -f docker-compose.simple.yml restart
echo.

:: Check if application is responding
curl -s http://localhost:5000/health >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Application might still be starting...
    echo    Check logs if issues persist: docker-compose -f docker-compose.simple.yml logs
) else (
    echo ✅ Application is running successfully!
)

echo.
pause
