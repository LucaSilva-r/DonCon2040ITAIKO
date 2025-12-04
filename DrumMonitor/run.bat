@echo off
REM DonCon2040 Drum Monitor Launcher for Windows

echo ========================================
echo  DonCon2040 Drum Monitor
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo Virtual environment not found. Setting up...
    echo.
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        echo Please ensure Python 3.7+ is installed.
        pause
        exit /b 1
    )
    echo Virtual environment created successfully.
    echo.
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Check if dependencies are installed
python -c "import pyqtgraph" 2>nul
if errorlevel 1 (
    echo Installing dependencies...
    echo.
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies.
        pause
        exit /b 1
    )
    echo Dependencies installed successfully.
    echo.
)

REM Run the application
echo Starting Drum Monitor...
echo.
python drum_monitor.py

REM Deactivate on exit
deactivate
