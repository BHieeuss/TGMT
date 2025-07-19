@echo off
title TGMT - Firewall Configuration

echo.
echo ========================================
echo   TGMT - Windows Firewall Configuration
echo ========================================
echo.
echo This script will configure Windows Firewall to allow
echo network access to your Face Attendance application.
echo.
echo ⚠️  You need to run this as Administrator!
echo.

:: Check if running as administrator
net session >nul 2>&1
if errorlevel 1 (
    echo [ERROR] This script must be run as Administrator!
    echo.
    echo Right-click on this file and select "Run as administrator"
    echo.
    pause
    exit /b 1
)

echo [INFO] Administrator privileges confirmed.
echo.

echo Choose an option:
echo.
echo 1. Allow TGMT Face Attendance through firewall
echo 2. Remove TGMT firewall rules
echo 3. Show current firewall status
echo 4. Exit
echo.
set /p choice="Enter your choice (1-4): "

if "%choice%"=="1" goto allow_access
if "%choice%"=="2" goto remove_rules
if "%choice%"=="3" goto show_status
if "%choice%"=="4" goto exit
goto invalid_choice

:allow_access
echo.
echo [INFO] Configuring Windows Firewall...

:: Allow Python through firewall
netsh advfirewall firewall add rule name="TGMT Python App" dir=in action=allow protocol=TCP localport=5000
netsh advfirewall firewall add rule name="TGMT Python App Out" dir=out action=allow protocol=TCP localport=5000

:: Allow HTTP traffic on port 80 (if needed)
netsh advfirewall firewall add rule name="TGMT HTTP" dir=in action=allow protocol=TCP localport=80
netsh advfirewall firewall add rule name="TGMT HTTP Out" dir=out action=allow protocol=TCP localport=80

:: Allow Docker if using Docker deployment
netsh advfirewall firewall add rule name="TGMT Docker" dir=in action=allow program="C:\Program Files\Docker\Docker\resources\bin\docker.exe"

echo.
echo ✅ Firewall rules added successfully!
echo.
echo Your Face Attendance application should now be accessible from:
echo - Other computers on your network
echo - Mobile devices on the same WiFi
echo.
pause
goto menu

:remove_rules
echo.
echo [INFO] Removing TGMT firewall rules...

netsh advfirewall firewall delete rule name="TGMT Python App"
netsh advfirewall firewall delete rule name="TGMT Python App Out"
netsh advfirewall firewall delete rule name="TGMT HTTP"
netsh advfirewall firewall delete rule name="TGMT HTTP Out"
netsh advfirewall firewall delete rule name="TGMT Docker"

echo.
echo ✅ Firewall rules removed successfully!
echo.
pause
goto menu

:show_status
echo.
echo [INFO] Current firewall status for TGMT:
echo.

netsh advfirewall firewall show rule name="TGMT Python App" 2>nul
if errorlevel 1 (
    echo No TGMT Python App rules found
) else (
    echo TGMT Python App rules are active
)

netsh advfirewall firewall show rule name="TGMT HTTP" 2>nul
if errorlevel 1 (
    echo No TGMT HTTP rules found
) else (
    echo TGMT HTTP rules are active
)

netsh advfirewall firewall show rule name="TGMT Docker" 2>nul
if errorlevel 1 (
    echo No TGMT Docker rules found
) else (
    echo TGMT Docker rules are active
)

echo.
pause
goto menu

:invalid_choice
echo.
echo [ERROR] Invalid choice. Please select 1-4.
echo.
goto menu

:menu
echo.
goto :eof

:exit
echo.
echo Goodbye!
echo.
