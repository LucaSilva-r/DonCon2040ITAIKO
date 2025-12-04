#!/bin/bash
# DonCon2040 Drum Monitor Launcher for Linux/Mac

echo "========================================"
echo " DonCon2040 Drum Monitor"
echo "========================================"
echo

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Setting up..."
    echo
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to create virtual environment."
        echo "Please ensure Python 3.7+ is installed."
        exit 1
    fi
    echo "Virtual environment created successfully."
    echo
fi

# Activate virtual environment
source venv/bin/activate

# Check if dependencies are installed
python -c "import pyqtgraph" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing dependencies..."
    echo
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to install dependencies."
        exit 1
    fi
    echo "Dependencies installed successfully."
    echo
fi

# Run the application
echo "Starting Drum Monitor..."
echo
python drum_monitor.py

# Deactivate on exit
deactivate
