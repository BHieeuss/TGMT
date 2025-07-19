@echo off
setlocal enabledelayedexpansion

title TGMT Face Attendance - Quick Deploy Test

echo.
echo ========================================
echo   TGMT Face Attendance Quick Deploy
echo ========================================
echo.
echo This script will help you quickly deploy and test the application
echo.

:menu
echo Choose deployment method:
echo.
echo 1. Deploy with Docker (Full features - may take longer)
echo 2. Deploy with Docker (Simple - faster, recommended)  
echo 3. Deploy with Python only (No Docker needed)
echo 4. View application logs
echo 5. Stop application
echo 6. Create backup
echo 7. View system requirements
echo 8. Get network access info
echo 9. Setup Internet access (for people on different networks)
echo 10. ☁️ Deploy to Cloud (24/7 - Recommended)
echo 11. Exit
echo.
set /p choice="Enter your choice (1-11): "

if "%choice%"=="1" goto docker_deploy
if "%choice%"=="2" goto simple_deploy
if "%choice%"=="3" goto manual_deploy
if "%choice%"=="4" goto view_logs
if "%choice%"=="5" goto stop_app
if "%choice%"=="6" goto create_backup
if "%choice%"=="7" goto system_requirements
if "%choice%"=="8" goto network_info
if "%choice%"=="9" goto internet_access
if "%choice%"=="10" goto cloud_deploy
if "%choice%"=="11" goto exit
goto invalid_choice

:docker_deploy
echo.
echo [INFO] Checking Docker installation...
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not installed!
    echo Please install Docker Desktop from: https://www.docker.com/products/docker-desktop
    pause
    goto menu
)

docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Compose is not installed!
    echo Please install Docker Compose
    pause
    goto menu
)

echo [INFO] Docker found! Starting deployment...
echo.

echo [INFO] Stopping any existing containers...
docker-compose down >nul 2>&1

echo [INFO] Building and starting application...
docker-compose up --build -d

echo.
echo [INFO] Waiting for application to start...
timeout /t 15 /nobreak >nul

echo [INFO] Checking application status...
curl -s http://localhost:5000/health >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Application might still be starting...
    echo [INFO] Check logs with: docker-compose logs -f face-attendance
) else (
    echo [SUCCESS] Application is running!
)

echo.
echo ========================================
echo   Deployment Complete!
echo ========================================
echo.
echo 🌐 Application URL: http://localhost:5000
echo 👤 Default credentials:
echo    Username: admin
echo    Password: admin123
echo.
echo 📊 Useful commands:
echo    View logs: docker-compose logs -f face-attendance
echo    Stop app:  docker-compose down
echo    Restart:   docker-compose restart
echo.
pause
goto menu

:simple_deploy
echo.
echo [INFO] Starting simple Docker deployment (recommended)...
simple-deploy.bat
pause
goto menu

:manual_deploy
echo.
echo [INFO] Starting Python deployment...
python-deploy.bat
pause
goto menu

:view_logs
echo.
echo [INFO] Viewing application logs...
docker-compose logs --tail=50 -f face-attendance
pause
goto menu

:stop_app
echo.
echo [INFO] Stopping applications...
docker-compose down >nul 2>&1
docker-compose -f docker-compose.simple.yml down >nul 2>&1
echo [INFO] All applications stopped successfully!
pause
goto menu

:network_info
echo.
echo ========================================
echo   Network Access Information
echo ========================================
echo.

:: Get computer's IP address
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4 Address"') do (
    set "ip=%%a"
    goto :found_ip_info
)
:found_ip_info
set "ip=%ip: =%"

echo Your computer's IP address: %ip%
echo.
echo 🌐 Share these URLs with others:
echo   - http://%ip%:5000
echo   - http://%ip% (if port 80 is mapped)
echo.
echo 📱 For mobile devices:
echo   Make sure they are on the same WiFi network
echo   Then access: http://%ip%:5000
echo.
echo 🔒 Security Notes:
echo   - This makes your app accessible to anyone on your network
echo   - Use firewall settings if you want to restrict access
echo   - Change default admin password for security
echo.
echo 🛠️ Troubleshooting:
echo   - If others can't access, check Windows Firewall
echo   - Allow Python/Docker through firewall
echo   - Make sure port 5000 is not blocked
echo.
pause
goto menu

:create_backup
echo.
echo [INFO] Creating backup...
if exist "backup.sh" (
    bash backup.sh
) else (
    echo [INFO] Creating manual backup...
    set backup_date=%date:~10,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
    set backup_date=!backup_date: =0!
    
    if not exist "backups" mkdir backups
    
    if exist "attendance_system.db" (
        copy "attendance_system.db" "backups\attendance_system_!backup_date!.db"
        echo [INFO] Database backed up successfully!
    )
    
    if exist "uploads" (
        tar -czf "backups\uploads_!backup_date!.tar.gz" uploads
        echo [INFO] Uploads backed up successfully!
    )
)
echo [INFO] Backup completed!
pause
goto menu

:system_requirements
echo.
echo ========================================
echo   System Requirements
echo ========================================
echo.
echo Minimum Requirements:
echo   - CPU: 2 cores
echo   - RAM: 4GB
echo   - Storage: 10GB free space
echo   - OS: Windows 10/11
echo.
echo Recommended:
echo   - CPU: 4+ cores  
echo   - RAM: 8GB+
echo   - Storage: 50GB+ SSD
echo   - Camera: USB webcam for face recognition
echo.
echo Software Requirements:
echo   - Docker Desktop (recommended)
echo   OR
echo   - Python 3.8+
echo   - Git
echo.
echo Ports Used:
echo   - 5000: Flask application
echo   - 80: Nginx (if enabled)
echo   - 443: HTTPS (if SSL configured)
echo.
pause
goto menu

:internet_access
echo.
echo [INFO] Setting up internet access for people on different networks...
internet-access.bat
pause
goto menu

:cloud_deploy
echo.
echo [INFO] Deploying to cloud for 24/7 operation...
cloud-deploy.bat
pause
goto menu

:invalid_choice
echo.
echo [ERROR] Invalid choice. Please select 1-11.
echo.
goto menu

:exit
echo.
echo Thank you for using TGMT Face Attendance System!
echo.
pause
