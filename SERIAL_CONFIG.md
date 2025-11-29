# Serial Configuration Guide

This document explains how to use the USB serial configuration interface for runtime parameter adjustment during testing.

## Overview

The serial configuration system allows you to read and modify controller settings via USB CDC serial connection without using the OLED menu. This is particularly useful for:
- Quick testing of different threshold values
- Automated configuration scripts
- Bulk parameter adjustments
- Remote configuration

## Protocol

The system uses a simple command-based protocol similar to hidtaiko's web configurator:

### Commands

**Configuration Commands:**
- **1000** - Read all settings (returns key:value pairs)
- **1001** - Save current settings to flash memory
- **1002** - Enter write mode (to send key:value pairs)
- **1003** - Reload settings from flash

**Streaming Commands:**
- **2000** - Start streaming sensor data (CSV format, ~100Hz)
- **2001** - Stop streaming sensor data

### Setting Keys (HIDtaiko-Compatible)

**Compatible with: https://kasasiki3.github.io/ver1.3_webapp_rp2040version/**

| Key | HIDtaiko Name | DonCon2040 Setting | Type | Description |
|-----|---------------|-------------------|------|-------------|
| 0 | Left Face | Don Left Threshold | uint32 | Left face (don) sensitivity |
| 1 | Left Rim | Ka Left Threshold | uint32 | Left rim (ka) sensitivity |
| 2 | Right Face | Don Right Threshold | uint32 | Right face (don) sensitivity |
| 3 | Right Rim | Ka Right Threshold | uint32 | Right rim (ka) sensitivity |
| 4 | B delay | Don Debounce | uint16 | Next input time after face hit (ms) |
| 5 | C delay | Kat Debounce | uint16 | Rim input acceptance time (ms) |
| 6 | D delay | Crosstalk Debounce | uint16 | Time to ignore rim after face (ms) |
| 7 | H delay | Key Timeout | uint16 | Input limit for simulators (ms) |
| 8 | A delay | Debounce Delay | uint16 | Key hold time (ms) |

### Extended Keys (DonCon2040-Specific)

| Key | Setting | Type | Description |
|-----|---------|------|-------------|
| 9 | Double Trigger Mode | uint16 | 0=Off, 1=Threshold |
| 10 | Double Trigger Don Left | uint32 | Left face double trigger threshold |
| 11 | Double Trigger Ka Left | uint32 | Left rim double trigger threshold |
| 12 | Double Trigger Don Right | uint32 | Right face double trigger threshold |
| 13 | Double Trigger Ka Right | uint32 | Right rim double trigger threshold |

**Note:** Extended keys (9-13) are **NOT** compatible with the hidtaiko web configurator. They can only be accessed via command-line tools or custom scripts.

## Usage Examples

### Using the Python Test Script

```bash
# Install pyserial if not already installed
pip install pyserial

# Read all current settings
python test_serial_config.py COM3 read

# Set don left threshold to 1000
python test_serial_config.py COM3 set 0 1000

# Save settings to flash
python test_serial_config.py COM3 save

# Reload settings from flash
python test_serial_config.py COM3 reload
```

### Manual Usage (Serial Terminal)

1. Connect to the COM port at 115200 baud
2. Send commands as plain text:

```
1000          # Read all settings
1002          # Enter write mode
0:1000        # Set don left threshold to 1000
1:900         # Set ka left threshold to 900
1001          # Save to flash
```

### Write Mode Details

When you send **1002**, the device enters write mode and accepts key:value pairs:
- Format: `key:value` (e.g., `0:800`)
- Multiple values can be sent space-separated: `0:800 1:900 2:800`
- Write mode automatically exits after **14 values** are received (9 hidtaiko + 5 extended)
- Values are applied immediately but not saved to flash until you send **1001**

### Streaming Mode

When you send **2000**, the device starts streaming sensor data:
- **Format:** CSV with triggered flags and raw ADC values
- **Example:** `F,200,T,1000,F,300,F,254` (ka_left, don_left, don_right, ka_right)
- **Rate:** ~100Hz (10ms between samples)
- **Stop:** Send **2001** to stop streaming

**CSV Format:**
```
triggered_ka_left,ka_raw,triggered_don_left,don_left_raw,triggered_don_right,don_right_raw,triggered_ka_right,ka_right_raw
```

**Usage:**
```bash
# Start streaming
python test_serial_config.py COM3 stream

# (In your script, read lines from serial port and parse CSV)

# Stop streaming
python test_serial_config.py COM3 stopstream
```

## Integration with Existing System

The serial configuration system:
- ✅ Integrates with existing `SettingsStore` class
- ✅ Respects the same value ranges and types
- ✅ Works alongside OLED menu system
- ✅ Changes made via serial are immediately applied to the Drum peripheral
- ✅ Changes persist across reboots when saved with command 1001
- ⚠️ Does NOT require menu system or cause settings conflicts
- ⚠️ Changes take effect immediately but must be saved manually

## Comparison with hidtaiko

| Feature | hidtaiko | DonCon2040 Serial Config |
|---------|----------|--------------------------|
| Protocol | Same command codes (1000-1003) | ✅ Same command codes + streaming (2000-2001) |
| Parameter Mapping | Keys 0-8 (9 values) | ✅ Keys 0-8 (9 values) + Keys 9-13 (5 extended) |
| Web Configurator | kasasiki3.github.io | ✅ **Fully Compatible!** (keys 0-8 only) |
| Value Storage | uint16_t (0-65535) | uint32_t for thresholds, uint16_t for delays |
| Integration | Standalone | Integrated with SettingsStore |
| Persistence | Manual flash write | Managed by SettingsStore |
| Streaming Mode | N/A | ✅ Commands 2000/2001 for live sensor data (~100Hz) |
| Extra Features | N/A | Double trigger settings (keys 9-13), sensor streaming |

## USB Mode Compatibility

Serial configuration requires a USB mode that includes CDC (serial) interface:

✅ **Keyboard P1/P2** - Includes CDC + HID (recommended for PC testing)
✅ **Debug** - CDC only (no controller functionality)
❌ **Other modes** (Switch, PS4, Xbox, MIDI) - HID/Vendor only, no CDC

**To use serial configuration:**
1. Switch to Keyboard mode via OLED menu
2. Connect to PC - it will appear as both a keyboard and COM port
3. Use the web configurator or Python script
4. Settings persist across all modes!

## Troubleshooting

**Settings not persisting:**
- Make sure to send command **1001** to save to flash
- Verify "Settings saved" message appears

**No response from device:**
- Check COM port is correct
- Ensure device is properly connected
- Try reconnecting USB cable
- Verify baudrate is 115200

**Changes not taking effect:**
- Settings are applied immediately when written
- If using the menu system simultaneously, menu changes may override serial changes
- Exit menu before using serial configuration

## Implementation Details

- **Location**: `src/utils/SerialConfig.cpp` and `include/utils/SerialConfig.h`
- **Main Loop**: Called from Core 0 main loop via `serial_config.processSerial()`
- **Non-blocking**: All operations are non-blocking and safe for main loop
- **Thread-safe**: Uses existing SettingsStore which handles thread safety
