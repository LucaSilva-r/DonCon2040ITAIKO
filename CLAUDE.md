# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DonCon2040 is a firmware for DIY Taiko no Tatsujin arcade-style drum controllers based on the RP2040 microcontroller. It's designed to be modular and extensible for specialized controller builds.

**Version**: 0.39.0 (see CMakeLists.txt)

## Build Commands

### VSCode Build
This project uses the Raspberry Pi Pico VSCode extension:
- **Build**: Use the Raspberry Pi Pico extension's 'Compile Project' command
- VSCode automatically configures CMake using settings in `.vscode/settings.json`

### CLI Build
```bash
mkdir build && cd build
cmake ..
make
```

Environment variables:
- `PICO_SDK_PATH`: Path to local Pico SDK (auto-fetches from GitHub if not set)
- `PICO_BOARD`: Target board selection (defaults to `waveshare_rp2040_zero`)

### Build Configuration
- CMake 3.13+, Pico SDK 2.2.0
- C11 for C code, C++20 for C++ code
- Compiler flags: `-Wall -Wextra -Werror`
- Default board: `waveshare_rp2040_zero`
- Outputs: ELF, MAP, BIN, HEX, and UF2 files

### Code Quality Tools
- **clang-format**: LLVM style, 4-space indentation, 120-column limit
- **clang-tidy**: Strict static analysis enabled (see `.clang-tidy` for full configuration)
  - Warnings as errors
  - Excludes TinyUSB and SSD1306 headers from analysis

## Directory Structure

```
DonCon2040ITAIKO/
├── src/                          # Source code (~3,300 lines C++)
│   ├── main.cpp                  # Entry point, dual-core setup (259 lines)
│   ├── peripherals/              # Hardware abstraction
│   │   ├── Drum.cpp              # Sensor input, debouncing (525 lines)
│   │   ├── Controller.cpp        # Button/D-pad via MCP23017 (125 lines)
│   │   ├── Display.cpp           # SSD1306 OLED rendering (204 lines)
│   │   └── StatusLed.cpp         # WS2812 LED control (68 lines)
│   ├── usb/                      # USB device driver stack (~2,100 lines)
│   │   ├── device_driver.c       # Mode selector, descriptors (154 lines)
│   │   ├── device/hid/           # HID-based controllers
│   │   │   ├── common.c          # HID base & report generation
│   │   │   ├── switch_driver.c   # Switch Tatacon/Horipad
│   │   │   ├── ps3_driver.c      # Dualshock 3
│   │   │   ├── ps4_driver.c      # PS4 Tatacon with auth (476 lines)
│   │   │   ├── keyboard_driver.c # Keyboard modes
│   │   │   └── ps4_auth.c        # PS4 challenge signing
│   │   ├── device/vendor/        # Vendor-specific protocols
│   │   │   ├── xinput_driver.c   # XInput & XInput Analog
│   │   │   └── debug_driver.c    # USB serial debug output
│   │   └── midi_driver.c         # MIDI output
│   └── utils/                    # Core utilities
│       ├── Menu.cpp              # Settings menu state machine (844 lines)
│       ├── InputReport.cpp       # USB HID report formatting (325 lines)
│       ├── SettingsStore.cpp     # Flash persistence (293 lines)
│       ├── SerialConfig.cpp      # USB CDC configuration (563 lines)
│       └── PS4AuthProvider.cpp   # PS4 auth integration
├── include/                      # Headers (~3,600 lines)
│   ├── GlobalConfiguration.h     # CRITICAL: All hardware config
│   ├── PS4AuthConfiguration.h    # Generated auth credentials (not in repo)
│   ├── peripherals/
│   │   ├── Drum.h                # Pad debouncing, ADC interfaces
│   │   ├── Controller.h          # SOCD cleaning, GPIO abstraction
│   │   ├── Display.h             # Display state machine
│   │   └── StatusLed.h           # RGB/RGBW LED support
│   ├── usb/device/
│   │   ├── device_driver.h       # USB mode enum, driver interface
│   │   ├── hid/*.h               # HID driver headers
│   │   └── vendor/*.h            # Vendor driver headers
│   └── utils/
│       ├── InputState.h          # Core data structures, queues
│       ├── Menu.h                # Menu state machine
│       ├── SettingsStore.h       # Flash storage interface
│       ├── SerialConfig.h        # Serial protocol
│       ├── KeyboardMappings.h    # Keyboard key structs
│       └── InputReport.h         # USB report generation
├── libs/                         # Reusable hardware libraries
│   ├── pico_ssd1306/             # SSD1306 OLED driver
│   ├── mcp23017/                 # I2C GPIO expander driver
│   ├── mcp3204/                  # SPI ADC driver (with DMA variant)
│   └── pio_ws2812/               # WS2812 LED driver via PIO
├── lib/                          # External dependencies (git submodules)
│   ├── tinyusb/                  # USB device stack
│   └── mbedtls/                  # Cryptography for PS4 auth
├── pcb/                          # Hardware designs
│   ├── DonConIO/                 # Main IO board
│   ├── DonConIOmini/             # Minimal board for Waveshare RP2040-Zero
│   └── DonConPad/                # Gamepad controller PCB
├── scripts/
│   ├── generateAuthConfig.py     # PS4 auth config generator
│   └── generateBitmap.py         # Bitmap image converter
└── .vscode/                      # IDE configuration
```

## High-Level Architecture

### Dual-Core Design
The firmware uses both RP2040 cores with distinct responsibilities:

**Core 0 (Main):**
- USB communication and HID report generation
- Menu system management and user interface
- PS4 authentication challenge signing (blocks core for 2-3s during signing)
- Serial configuration protocol (USB CDC)
- Main event loop coordinating all subsystems
- Entry point: `main.cpp`

**Core 1 (Peripheral Handler):**
- Controller input polling (buttons, D-pad via I2C GPIO expander)
- Display rendering (OLED via I2C)
- Status LED control (WS2812 via PIO)
- Drum sensor reading and aggregation
- Launched from `main.cpp` via `multicore_launch_core1()`

### Inter-Core Communication
The cores communicate via **thread-safe queues** defined in `include/utils/InputState.h`:
- `control_queue`: Settings and mode changes (Core 0 → Core 1)
- `menu_display_queue`: Menu state updates (Core 0 → Core 1)
- `drum_input_queue`: Drum sensor data (Core 1 → Core 0)
- `controller_input_queue`: Button/gamepad input (Core 1 → Core 0)
- `auth_challenge_queue` / `auth_signed_challenge_queue`: PS4 authentication (bidirectional)

### USB Device Driver Architecture
The USB subsystem (`src/usb/`) is organized by device class:

**HID Drivers** (`src/usb/device/hid/`):
- Each emulation mode has its own driver (PS4, PS3, Switch, keyboard)
- Common HID utilities in `common.c`
- PS4 authentication in `ps4_auth.c`

**Vendor Drivers** (`src/usb/device/vendor/`):
- XInput protocol for Xbox 360 emulation (`xinput_driver.c`)
- Debug mode with USB serial output (`debug_driver.c`)

**Driver Abstraction** (`src/usb/device_driver.c`):
- Provides unified interface across all USB modes
- Mode switching handled at runtime based on settings

### Input Processing Pipeline
1. **Sensor Acquisition** (`src/peripherals/Drum.cpp`):
   - Analog input from internal ADC or external MCP3204 SPI ADC
   - 4 pads: Don Left/Right, Ka Left/Right
   - ADC channels configurable per-pad without recompile

2. **Debouncing** (multiple independent timers):
   - Global debounce (minimum time between any inputs)
   - Don-to-Don debounce (side lockout)
   - Ka-to-Ka debounce (side lockout)
   - Crosstalk debounce (don→ka lockout)
   - Key timeout (input duration sent to USB)

3. **Double Trigger Detection**:
   - Automatically triggers both sides if single hit exceeds threshold
   - Weighted comparison mode for analog ratio distribution

4. **State Aggregation** (`include/utils/InputState.h`):
   - Unified `InputState` struct combines drum and button inputs
   - Drumroll counter with configurable timeout

5. **Report Generation** (`src/utils/InputReport.cpp`):
   - Converts `InputState` to USB HID reports
   - Format depends on active emulation mode

6. **USB Transmission**:
   - TinyUSB device stack sends reports to host
   - Mode-specific descriptors and report formats

### Configuration System

**Runtime Configuration** (Menu accessible via Start+Select for 2 seconds):
- Controller emulation mode selection (12 modes available)
- LED brightness and player color toggle
- Per-pad trigger thresholds
- Per-pad cutoff thresholds
- Debounce/hold time (don/ka/crosstalk separate)
- Double trigger mode (Off/Threshold) and thresholds
- Settings persisted to flash via `src/utils/SettingsStore.cpp`

**Serial Configuration** (`src/utils/SerialConfig.cpp`):
- USB CDC serial interface for remote configuration
- Commands:
  - `1000`: Read all settings (key:value format)
  - `1001`: Save to flash
  - `1002`: Enter write mode
  - `1003`: Reload from flash
  - `1004`: Reboot to BOOTSEL
  - `2000`/`2001`: Stream sensor data (~100Hz CSV)
- Keys 0-8: HIDtaiko-compatible (works with kasasiki3.github.io web configurator)
- Keys 9-45: Extended DonCon2040 features (double trigger, cutoff, keyboard mappings, ADC channels)
- Test script: `test_serial_config.py`

**Compile-Time Configuration** (`include/GlobalConfiguration.h`):
- Hardware pin assignments (I2C, SPI, ADC, LEDs)
- I2C addresses (OLED @ 0x3C, GPIO expander @ 0x20)
- Default thresholds and debounce values
- Button mappings for all 12 USB modes
- LED colors per emulation mode
- ADC configuration (internal vs external MCP3204)
- Two example configs included (standard & DonConIO)

**PS4 Authentication** (`include/PS4AuthConfiguration.h`):
- Generated by `scripts/generateAuthConfig.py`
- Requires serial, signature, and private key from original DS4
- Not included in repository for legal reasons

## Hardware Peripherals

- **Display**: SSD1306 OLED (128x64, I2C @ 0x3C) - driver in `libs/pico_ssd1306`
- **GPIO Expansion**: MCP23017 (I2C @ 0x20) - driver in `libs/mcp23017`
- **ADC**: Internal RP2040 ADC or external MCP3204 (SPI) - driver in `libs/mcp3204`
- **LED**: WS2812 RGB via PIO - driver in `libs/pio_ws2812`
- **Sensors**: Sensatec GSS-4S* piezo impact sensors (analog output)

I2C Configuration:
- SDA Pin: 6, SCL Pin: 7
- Bus: i2c1
- Speed: 1 MHz

## Key Files and Their Roles

| File | Lines | Purpose |
|------|-------|---------|
| `src/main.cpp` | 259 | Core orchestration, dual-core setup, USB/menu handling |
| `src/peripherals/Drum.cpp` | 525 | 4-pad trigger acquisition, debouncing, double trigger logic |
| `src/peripherals/Controller.cpp` | 125 | Button and D-pad input via MCP23017 |
| `src/utils/Menu.cpp` | 844 | On-screen settings menu (~30 pages, complex state machine) |
| `src/utils/InputReport.cpp` | 325 | USB HID report generation for all 12 modes |
| `src/utils/SettingsStore.cpp` | 293 | Flash memory persistence with wear leveling |
| `src/utils/SerialConfig.cpp` | 563 | USB CDC serial configuration protocol |
| `src/usb/device/hid/ps4_driver.c` | 476 | PS4 Tatacon driver with authentication |
| `include/GlobalConfiguration.h` | - | **Primary configuration file** - edit for hardware customization |
| `include/utils/InputState.h` | 48 | Core data structures and queue definitions |

## USB Controller Modes

The firmware supports 12 emulation modes (changeable at runtime):

| ID | Name | Type | Notes |
|----|------|------|-------|
| 0 | Switch Tatacon | HID | Default, HORI NSW-079, no auth |
| 1 | Switch Horipad | HID | Pro Controller, D-pad mode |
| 2 | PS3 Dualshock3 | HID | Full compatibility |
| 3 | PS4 Tatacon | HID | HORI PS4-095, requires PS4AuthConfiguration.h |
| 4 | PS4 Dualshock4 | HID | **PC/Steam only, NO PS4 console** |
| 5 | Keyboard P1 | HID | DFJK mapping |
| 6 | Keyboard P2 | HID | CBN, mapping (configurable via serial) |
| 7 | XInput | Vendor | Xbox 360 compatibility |
| 8 | XInput Analog P1 | Vendor | Analog triggers for TaikoArcadeLoader |
| 9 | XInput Analog P2 | Vendor | Analog triggers P2 |
| 10 | MIDI | Vendor | Note on/off output |
| 11 | Debug | Vendor | USB serial output, raw state dump |

## ADC Configuration Examples

**Internal ADC (Default):**
```cpp
.adc_config = Peripherals::Drum::Config::InternalAdc{
    .sample_count = 16,  // Averaging
}
```

**External SPI ADC (MCP3204):**
```cpp
.adc_config = Peripherals::Drum::Config::ExternalAdc{
    .spi_block = spi1,
    .spi_speed_hz = 2000000,
    .spi_mosi_pin = 11,
    .spi_miso_pin = 12,
    .spi_sclk_pin = 10,
    .spi_scsn_pin = 13,
    .spi_level_shifter_enable_pin = 9,
}
```

## Button Input Configuration

**Internal GPIO (built-in RP2040 pins):**
```cpp
.gpio_config = Peripherals::Controller::Config::InternalGpio{}
```

**External MCP23017 (for additional buttons):**
```cpp
.gpio_config = Peripherals::Controller::Config::ExternalGpio{
    .i2c = { .block = i2c1, .address = 0x20 }
}
```

## Development Notes

- **Display and buttons are mandatory** - controller won't function without MCP23017 and SSD1306
- PS4 authentication blocks Core 1 for 2-3 seconds during signing (display/LED freeze, drum input unaffected)
- Debounce delay implicitly serves as hold time - increase if inputs are dropped (min 25ms for Switch)
- No dedicated test framework - use Debug mode with USB serial for troubleshooting
- Libraries in `libs/` are designed to be reusable in other RP2040 projects
- Project is designed as a base for specialized controllers (see DivaCon2040 as example)
- Flash wear leveling: SettingsStore uses 4-page rotation in last 4KB sector
- HIDtaiko compatibility: SerialConfig keys 0-8 work with kasasiki3.github.io web configurator

## Menu System Pages

The menu (`src/utils/Menu.cpp`) has approximately 30 pages organized as:
- **Device Mode**: Select 1 of 12 USB emulation modes
- **Drum Settings**: Hold time, debounce delays (don/ka/crosstalk), thresholds per-pad
- **Double Trigger**: Off or Threshold mode with separate thresholds
- **Cutoff Thresholds**: Per-pad cutoff values
- **LED Settings**: Brightness and player color toggle
- **System**: Version display, Reset to defaults, Reboot to BOOTSEL

Navigation: D-pad with button repeat logic. Triggered by holding Start+Select for 2 seconds.

## Dependencies

**External (Git Submodules in lib/):**
- `tinyusb`: USB device stack
- `mbedtls`: Cryptography library (for PS4 authentication)

**Internal Libraries (libs/):**
- `pico_ssd1306`: OLED display driver (full C API)
- `mcp23017`: GPIO expander wrapper (C++ class)
- `mcp3204`: SPI ADC driver (C API, optional DMA variant in Mcp3204Dma.h)
- `pio_ws2812`: WS2812 LED driver via PIO (C API with gamma correction)

## CI/CD

- GitHub Actions workflow: `.github/workflows/pico build.yml`
- Semantic versioning with automatic releases
- Releases include: UF2, ELF, BIN, HEX artifacts
- Configuration: `.releaserc.json`
