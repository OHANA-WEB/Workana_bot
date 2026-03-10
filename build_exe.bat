@echo off
echo ========================================
echo Workana Bot - Build Executable
echo ========================================
echo.

echo Step 1: Installing PyInstaller...
pip install pyinstaller
if errorlevel 1 (
    echo Failed to install PyInstaller. Please install manually: pip install pyinstaller
    pause
    exit /b 1
)

echo.
echo Step 2: Building executable...
python build_exe.py
if errorlevel 1 (
    echo Build failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build complete!
echo ========================================
echo.
echo The executable is located in: dist\workana_bot.exe
echo.
echo IMPORTANT: Before running the executable:
echo 1. Copy your .env file to the same folder as workana_bot.exe
echo 2. Install Playwright browsers (run once):
echo    workana_bot.exe --install-browsers
echo    OR manually: playwright install chromium
echo.
pause
