@echo off
REM ============================================================================
REM  DeskBuddy 1-Click Windows Setup & Installer
REM  Automatically configures virtual environment, installs dependencies,
REM  and generates a Desktop Shortcut with icon.
REM ============================================================================
setlocal enabledelayedexpansion
pushd "%~dp0"
title DeskBuddy Setup

echo =======================================================
echo        Welcome to the DeskBuddy Installer! 🐾
echo =======================================================
echo.

REM 1. Check for Python
echo [1/4] Checking Python installation...
set "PYTHON_CMD="

REM Check py launcher
py -0 >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=py"
    goto :python_found
)

REM Check default python
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=python"
    goto :python_found
)

REM Check common AppData Python installs
if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" (
    set "PYTHON_CMD="%LOCALAPPDATA%\Programs\Python\Python314\python.exe""
    goto :python_found
)
if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    set "PYTHON_CMD="%LOCALAPPDATA%\Programs\Python\Python313\python.exe""
    goto :python_found
)
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PYTHON_CMD="%LOCALAPPDATA%\Programs\Python\Python312\python.exe""
    goto :python_found
)

REM If Python is missing, offer automatic installation via winget
echo [!] Python was not detected on your system.
echo     DeskBuddy can automatically install Python for you via Windows Package Manager (winget).
set /p INSTALL_PY="Would you like to install Python 3.12 now? (Y/N): "
if /i "%INSTALL_PY%"=="Y" (
    echo [*] Installing Python 3.12 via winget...
    winget install Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
    if %errorlevel% equ 0 (
        echo [*] Python installed successfully! Please restart this setup script.
        pause
        popd
        exit /b 0
    ) else (
        echo [X] Winget installation failed. Please install Python 3.10+ manually from https://python.org
        pause
        popd
        exit /b 1
    )
) else (
    echo [X] Python is required to run DeskBuddy. Please install Python 3.10+ and re-run this setup.
    pause
    popd
    exit /b 1
)

:python_found
echo [*] Detected Python command: %PYTHON_CMD%
echo.

REM 2. Create isolated virtual environment
echo [2/4] Setting up isolated Python environment (.venv_win)...
if not exist ".venv_win\Scripts\python.exe" (
    %PYTHON_CMD% -m venv .venv_win
    if %errorlevel% neq 0 (
        echo [X] Failed to create virtual environment. Please check Python permissions.
        pause
        popd
        exit /b 1
    )
)
echo [*] Environment ready!
echo.

REM 3. Install Requirements
echo [3/4] Installing DeskBuddy dependencies...
call .venv_win\Scripts\activate.bat
python -m pip install --upgrade pip >nul 2>&1
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [!] Warning: Some optional packages could not be installed. Core features will still work!
) else (
    echo [*] Dependencies installed successfully!
)
echo.

REM 4. Create Desktop Shortcut with Icon
echo [4/4] Creating Desktop Shortcut...
set "SCRIPT_DIR=%~dp0"
set "LAUNCH_BAT=%SCRIPT_DIR%run.bat"
set "ICON_PATH=%SCRIPT_DIR%assets\tray_icon.ico"

REM If .ico does not exist, fallback to png or generic
if not exist "%ICON_PATH%" (
    set "ICON_PATH=%SCRIPT_DIR%assets\tray_icon.png"
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ws = New-Object -ComObject WScript.Shell; " ^
    "$s = $ws.CreateShortcut([System.IO.Path]::Combine([Environment]::GetFolderPath('Desktop'), 'DeskBuddy.lnk')); " ^
    "$s.TargetPath = '%LAUNCH_BAT%'; " ^
    "$s.WorkingDirectory = '%SCRIPT_DIR%'; " ^
    "$s.IconLocation = '%ICON_PATH%'; " ^
    "$s.Description = 'DeskBuddy - Interactive Desktop Companion'; " ^
    "$s.Save()"

if %errorlevel% equ 0 (
    echo [*] Desktop Shortcut created successfully: "DeskBuddy" on your Desktop!
) else (
    echo [!] Notice: Could not create desktop shortcut automatically. You can launch DeskBuddy anytime via run.bat.
)
echo.

echo =======================================================
echo          🎉 DeskBuddy is completely ready! 🎉
echo =======================================================
echo.
set /p LAUNCH_NOW="Would you like to launch DeskBuddy right now? (Y/N): "
if /i "%LAUNCH_NOW%"=="Y" (
    echo [*] Launching DeskBuddy...
    start "" "%LAUNCH_BAT%"
)

popd
endlocal
exit /b 0
