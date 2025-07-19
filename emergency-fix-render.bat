@echo off
title TGMT - EMERGENCY FIX - Force Python 3.10

echo.
echo ========================================
echo   🚨 EMERGENCY FIX - FORCE PYTHON 3.10
echo ========================================
echo.

echo [ERROR ANALYSIS] Render vẫn đang dùng Python 3.13 dù đã fix!
echo [SOLUTION] Force rebuild hoàn toàn với Python 3.10.12
echo.

echo ✅ EMERGENCY FIXES:
echo   • Force Python 3.10.12-slim-bullseye (cụ thể)
echo   • Chỉ cài các package tối thiểu nhất
echo   • Cài từng package riêng biệt để debug
echo   • Dùng gunicorn thay vì python app.py
echo   • Clear cache build của Render
echo.

echo [STEP 1] Xóa file cache và tạo commit mới hoàn toàn...
if exist "Dockerfile.render.new" del "Dockerfile.render.new"

echo [STEP 2] Adding all changes với message đặc biệt...
git add .
git commit -m "🚨 EMERGENCY: Force Python 3.10.12 - Clear Render cache build"

echo [STEP 3] Force push để clear cache...
git push --force origin main

if errorlevel 1 (
    echo [ERROR] Push failed! Check git credentials.
    pause
    exit /b 1
)

echo.
echo ========================================
echo   ✅ EMERGENCY FIX DEPLOYED!
echo ========================================
echo.
echo 🔥 ĐÃ FORCE DEPLOY VỚI:
echo   • Python 3.10.12-slim-bullseye (exact version)
echo   • Minimal packages (chỉ Flask + Gunicorn)
echo   • Individual package install (debug friendly)
echo   • Force push để clear Render cache
echo.
echo ⏳ Render sẽ rebuild hoàn toàn từ đầu...
echo 🌐 Monitor Dashboard Render ngay!
echo.
echo 💡 QUAN TRỌNG:
echo   - Build này chỉ có web interface cơ bản
echo   - KHÔNG có face recognition (sẽ add sau)
echo   - Tập trung vào deploy thành công trước
echo.
echo 📱 URL sẽ là: https://tgmt-face-attendance.onrender.com
echo.
pause
