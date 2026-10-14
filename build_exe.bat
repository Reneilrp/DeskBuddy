@echo off
REM ============================================================================
REM  DeskBuddy Standalone Executable Builder (PyInstaller)
REM  Compiles DeskBuddy into a standalone portable distribution in dist/DeskBuddy/
REM  that requires NO Python installation for end users!
REM ============================================================================
setlocal enabledelayedexpansion
pushd "%~dp0"
title Build DeskBuddy Standalone Executable

echo =======================================================
echo         Building DeskBuddy Standalone .EXE 📦
echo =======================================================
echo.

if not exist ".venv_win\Scripts\python.exe" (
    echo [!] Virtual environment not found. Please run install.bat first!
    pause
    popd
    exit /b 1
)

call .venv_win\Scripts\activate.bat

echo [*] Ensuring PyInstaller is installed...
pip install pyinstaller >nul 2>&1

echo [*] Compiling DeskBuddy with PyInstaller...
pyinstaller --clean --noconfirm DeskBuddy.spec

if %errorlevel% equ 0 (
    echo.
    echo =======================================================
    echo   🎉 Build successful!
    echo   Standalone app location: dist\DeskBuddy\DeskBuddy.exe
    echo   You can zip the dist\DeskBuddy folder and distribute it!
    echo =======================================================
) else (
    echo.
    echo [X] Build encountered errors. Please check the log output above.
)

pause
popd
endlocal
