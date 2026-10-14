@echo off
REM DeskBuddy Windows Launcher with Smart Python Auto-Detection
setlocal enabledelayedexpansion
pushd "%~dp0"

echo [DeskBuddy] Finding Python installation...

set "PYTHON_EXE="

REM 1. Check if virtual environment already exists
if exist ".venv_win\Scripts\python.exe" (
    set "PYTHON_EXE=.venv_win\Scripts\python.exe"
    goto :launch
)

REM 2. Check py launcher
py -0 >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=py"
    goto :found_cmd
)

REM 3. Check AppData Python314
if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" (
    set "PYTHON_CMD="%LOCALAPPDATA%\Programs\Python\Python314\python.exe""
    goto :found_cmd
)

REM 4. Check explicit path
if exist "C:\Users\ASUS TUF A5\AppData\Local\Programs\Python\Python314\python.exe" (
    set "PYTHON_CMD="C:\Users\ASUS TUF A5\AppData\Local\Programs\Python\Python314\python.exe""
    goto :found_cmd
)

REM 5. Check default python in PATH
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=python"
    goto :found_cmd
)

echo [DeskBuddy Error] Python was not found on your system!
echo Please make sure Python 3 is installed or added to PATH.
pause
popd
exit /b 1

:found_cmd
echo [DeskBuddy] Using Python: %PYTHON_CMD%
if not exist ".venv_win\Scripts\python.exe" (
    echo [DeskBuddy] Creating Windows virtual environment in .venv_win...
    %PYTHON_CMD% -m venv .venv_win
    if %errorlevel% neq 0 (
        echo [DeskBuddy Error] Failed to create .venv_win.
        pause
        popd
        exit /b 1
    )
    echo [DeskBuddy] Installing requirements into .venv_win...
    call .venv_win\Scripts\activate.bat
    python -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [DeskBuddy Warning] Some packages had installation issues.
    )
)

set "PYTHON_EXE=.venv_win\Scripts\python.exe"

:launch
echo [DeskBuddy] Launching DeskBuddy...
%PYTHON_EXE% main.py %*

if %errorlevel% neq 0 (
    echo [DeskBuddy] Application exited with code %errorlevel%.
    pause
)

popd
endlocal
