@echo off
echo ============================================
echo   Basecoat SEO Image Tool - Build Script
echo ============================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo Download from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/3] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo [2/3] Building EXE with PyInstaller...
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "Basecoat SEO Tool" ^
    --add-data "config.json;." ^
    app.py

echo.
if exist "dist\Basecoat SEO Tool.exe" (
    echo [3/3] SUCCESS! Your EXE is ready at:
    echo       dist\Basecoat SEO Tool.exe
    echo.
    echo You can move this EXE anywhere on your PC.
    echo The config.json will be created next to it on first run.
) else (
    echo ERROR: Build failed. Check the output above for errors.
)

echo.
pause
