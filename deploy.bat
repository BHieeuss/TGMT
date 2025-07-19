@echo off
title TGMT Face Attendance System Deployment

echo.
echo ========================================
echo   TGMT Face Attendance System Deploy
echo ========================================
echo.

:: Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not installed. Please install Docker Desktop first.
    pause
    exit /b 1
)

:: Check if Docker Compose is installed
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Compose is not installed. Please install Docker Compose first.
    pause
    exit /b 1
)

echo [INFO] Stopping existing containers...
docker-compose down

echo.
echo [INFO] Building and starting containers...
docker-compose up --build -d

echo.
echo [INFO] Waiting for containers to be ready...
timeout /t 10 /nobreak >nul

echo.
echo [INFO] Checking container status...
docker-compose ps

echo.
echo ========================================
echo   Deployment Complete!
echo ========================================
echo.
echo Application is running at:
echo   - http://localhost:5000 (Direct Flask)
echo   - http://localhost (Through Nginx - if enabled)
echo.
echo Default login credentials:
echo   - Username: admin
echo   - Password: admin123
echo.
echo Useful commands:
echo   - View logs: docker-compose logs -f face-attendance
echo   - Stop app: docker-compose down
echo   - Restart: docker-compose restart
echo.
pause
