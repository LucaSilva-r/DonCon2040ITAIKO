# DonCon2040 Drum Monitor

Real-time ADC visualization tool for debugging and calibrating drum pad sensors.

![Screenshot](screenshot.png)

## Features

- **Real-time plotting** of all 4 drum pad ADC values at up to 1000Hz
- **Visual trigger indicators** - plots flash when pads are triggered
- **Threshold reference lines** - see your configured trigger thresholds
- **CSV data logging** - record sessions for later analysis
- **Adjustable settings** - update rate, history length, etc.
- **Auto-detection** of DonCon2040 devices (Raspberry Pi Pico)
- **Dark theme** UI with color-coded pads

## Requirements

- Python 3.7 or higher
- DonCon2040 firmware set to **Debug mode** (USB_MODE_DEBUG)

## Installation

### Windows

1. Open Command Prompt in this directory
2. Create a virtual environment:
   ```cmd
   python -m venv venv
   ```
3. Activate the virtual environment:
   ```cmd
   venv\Scripts\activate
   ```
4. Install dependencies:
   ```cmd
   pip install -r requirements.txt
   ```

### Linux/Mac

1. Open terminal in this directory
2. Create a virtual environment:
   ```bash
   python3 -m venv venv
   ```
3. Activate the virtual environment:
   ```bash
   source venv/bin/activate
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Quick Start (Windows)

Simply double-click `run.bat` (after completing installation above)

### Manual Start

1. Activate virtual environment:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`

2. Run the application:
   ```bash
   python drum_monitor.py
   ```

3. In the application:
   - Select your DonCon2040 device from the port dropdown
   - Click **Connect**
   - Start hitting your drums!

## Controls

### Connection Panel
- **Port**: Select the serial port (DonCon2040 devices are auto-labeled)
- **Refresh**: Refresh the list of available ports
- **Connect/Disconnect**: Toggle connection to the device

### Display Settings
- **Update Rate (ms)**: How often to refresh the display (lower = faster, higher CPU usage)
- **History (samples)**: Number of data points to display (higher = more history shown)

### Data Management
- **Log to CSV**: Enable to save all incoming data to a timestamped CSV file
- **Clear**: Clear all displayed data (useful for fresh calibration runs)

## Calibration Workflow

1. **Set thresholds to minimum** in DonCon2040 menu (to see raw values without triggering)
2. **Connect** the drum monitor
3. **Tap each pad lightly** - observe the baseline noise level
4. **Hit each pad at different strengths** - observe the peak values
5. **Determine your thresholds**:
   - Should be above noise level (typically ~100-200)
   - Should be below your lightest intended hit (~300-500)
6. **Update thresholds** in DonCon2040 menu
7. **Test** - the plots will flash when triggered
8. **Fine-tune** as needed

## Pad Colors

- **Ka Left** - Red
- **Don Left** - Blue
- **Don Right** - Green
- **Ka Right** - Orange

## Output Format

The firmware outputs CSV data in this format:
```
triggered_ka_left,ka_raw,triggered_don_left,don_left_raw,triggered_don_right,don_right_raw,triggered_ka_right,ka_right_raw
```

Example:
```
F,200,T,1000,F,300,F,254
```
- `T` = Triggered, `F` = Not triggered
- Numbers are raw 12-bit ADC values (0-4095)

## Troubleshooting

### "No ports found"
- Make sure DonCon2040 is connected via USB
- Ensure it's in **Debug mode** (check the OLED display)
- Try clicking **Refresh** after connecting the device

### Application won't start
- Verify Python 3.7+ is installed: `python --version`
- Ensure virtual environment is activated (you should see `(venv)` in your prompt)
- Reinstall dependencies: `pip install -r requirements.txt --force-reinstall`

### Plots are laggy
- Increase the **Update Rate** (try 20-50ms)
- Reduce the **History** buffer size
- Close other applications to free up CPU

### Data looks wrong
- Verify firmware is in Debug mode
- Check that you've built and flashed the latest firmware with CSV output format
- Try disconnecting and reconnecting

## Log Files

When logging is enabled, CSV files are saved with the format:
```
drum_log_YYYYMMDD_HHMMSS.csv
```

These can be opened in Excel, Python (pandas), MATLAB, etc. for detailed analysis.

## Advanced Usage

### Adjusting Threshold Lines

Edit `drum_monitor.py` line 45 to change the threshold reference lines:
```python
self.thresholds = [450, 350, 350, 450]  # Ka_L, Don_L, Don_R, Ka_R
```

### Export Plot Images

Right-click on any plot and choose "Export" to save as PNG, SVG, or CSV.

## Credits

Built with:
- [PyQtGraph](https://www.pyqtgraph.org/) - High-performance plotting
- [PySerial](https://pyserial.readthedocs.io/) - Serial communication
- [PyQt5](https://www.riverbankcomputing.com/software/pyqt/) - GUI framework
