#!/usr/bin/env python3
"""
Serial Configuration Test Tool for DonCon2040

Usage:
  python test_serial_config.py <PORT> [command]

Commands:
  read         - Read all settings (sends 1000)
  save         - Save settings to flash (sends 1001)
  write        - Enter write mode and send settings (sends 1002 + key:value pairs)
  reload       - Reload settings from flash (sends 1003)
  set <k> <v>  - Set specific key to value in write mode
  stream       - Start streaming sensor data (sends 2000)
  stream_input - Start streaming input status (sends 2002)
  stopstream   - Stop streaming sensor data (sends 2001)

Examples:
  python test_serial_config.py COM3 read
  python test_serial_config.py COM3 set 0 1000
  python test_serial_config.py COM3 save
"""

import serial
import time
import sys


class SerialConfig:
    """Serial configuration interface for DonCon2040"""

    # HIDtaiko-compatible mapping (web page order - keys 0&1 swapped!)
    SETTING_NAMES = {
        0: "Don Left / Left Face (sensitivity)",
        1: "Ka Left / Left Rim (sensitivity)",
        2: "Don Right / Right Face (sensitivity)",
        3: "Ka Right / Right Rim (sensitivity)",
        4: "Don Debounce / B delay (ms)",
        5: "Kat Debounce / C delay (ms)",
        6: "Crosstalk Debounce / D delay (ms)",
        7: "Key Timeout / H delay (ms)",
        8: "Debounce Delay / A delay - key hold time (ms)",
        9: "Double Trigger Mode (0=Off, 1=Threshold)",
        10: "Double Trigger Don Left Threshold",
        11: "Double Trigger Ka Left Threshold",
        12: "Double Trigger Don Right Threshold",
        13: "Double Trigger Ka Right Threshold"
    }

    def __init__(self, port, baudrate=115200):
        self.ser = serial.Serial(port, baudrate, timeout=2)
        time.sleep(0.1)  # Wait for connection

    def send_command(self, command):
        """Send a command code"""
        self.ser.write(f"{command}\n".encode())
        self.ser.flush()

    def read_all(self):
        """Read all settings"""
        print("Reading all settings...")
        self.send_command(1000)
        time.sleep(0.2)

        settings = {}
        while self.ser.in_waiting:
            line = self.ser.readline().decode().strip()
            if ':' in line:
                key, value = line.split(':')
                key = int(key)
                value = int(value)
                name = self.SETTING_NAMES.get(key, f"Unknown ({key})")
                settings[key] = value
                print(f"  [{key}] {name}: {value}")

        return settings

    def save_to_flash(self):
        """Save settings to flash"""
        print("Saving settings to flash...")
        self.send_command(1001)
        time.sleep(0.5)
        print("Done!")

    def reload_from_flash(self):
        """Reload settings from flash"""
        print("Reloading settings from flash...")
        self.send_command(1003)
        time.sleep(0.2)
        return self.read_response()

    def enter_write_mode(self):
        """Enter write mode"""
        print("Entering write mode...")
        self.send_command(1002)
        time.sleep(0.1)

    def set_value(self, key, value):
        """Set a specific key to a value"""
        self.enter_write_mode()
        time.sleep(0.1)

        data = f"{key}:{value}\n"
        print(f"Setting key {key} ({self.SETTING_NAMES.get(key, 'Unknown')}) = {value}")
        self.ser.write(data.encode())
        self.ser.flush()
        time.sleep(0.1)

        # Read response
        while self.ser.in_waiting:
            line = self.ser.readline().decode().strip()
            print(f"  Response: {line}")

    def start_streaming(self):
        """Start streaming sensor data"""
        print("Starting sensor data streaming...")
        self.send_command(2000)
        time.sleep(0.1)
        print("Streaming started. Press Ctrl+C to stop.")
        try:
            while True:
                if self.ser.in_waiting:
                    line = self.ser.readline().decode().strip()
                    try:
                        # Parse 64-bit hex string
                        val = int(line, 16)
                        # Unpack: KaL(48-63), DonL(32-47), DonR(16-31), KaR(0-15)
                        ka_l = (val >> 48) & 0xFFFF
                        don_l = (val >> 32) & 0xFFFF
                        don_r = (val >> 16) & 0xFFFF
                        ka_r = val & 0xFFFF
                        print(f"KL:{ka_l:<5} DL:{don_l:<5} DR:{don_r:<5} KR:{ka_r:<5} ({line})")
                    except ValueError:
                        print(line)
        except KeyboardInterrupt:
            print("\nStopping stream...")
            self.stop_streaming()

    def start_input_streaming(self):
        """Start streaming input status"""
        print("Starting input status streaming...")
        self.send_command(2002)
        time.sleep(0.1)
        print("Streaming started. Press Ctrl+C to stop.")
        try:
            while True:
                if self.ser.in_waiting:
                    line = self.ser.readline().decode().strip()
                    try:
                        mask = int(line, 16)
                        kl = "X" if (mask & 1) else "."
                        dl = "O" if (mask & 2) else "."
                        dr = "O" if (mask & 4) else "."
                        kr = "X" if (mask & 8) else "."
                        print(f"{kl} {dl} {dr} {kr} ({line})")
                    except ValueError:
                        print(line)
        except KeyboardInterrupt:
            print("\nStopping stream...")
            self.stop_streaming()

    def stop_streaming(self):
        """Stop streaming sensor data"""
        print("Stopping sensor data streaming...")
        self.send_command(2001)
        time.sleep(0.1)
        print("Streaming stopped.")

    def read_response(self):
        """Read and print any response"""
        time.sleep(0.1)
        responses = []
        while self.ser.in_waiting:
            line = self.ser.readline().decode().strip()
            print(f"  {line}")
            responses.append(line)
        return responses

    def close(self):
        """Close serial connection"""
        self.ser.close()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nAvailable COM ports:")
        import serial.tools.list_ports
        for port in serial.tools.list_ports.comports():
            print(f"  {port.device}: {port.description}")
        return

    port = sys.argv[1]
    command = sys.argv[2] if len(sys.argv) > 2 else "read"

    try:
        config = SerialConfig(port)

        if command == "read":
            config.read_all()
        elif command == "save":
            config.save_to_flash()
        elif command == "reload":
            config.reload_from_flash()
        elif command == "write":
            # Example: write all default values (extended format)
            config.enter_write_mode()
            time.sleep(0.1)

            # Send all 14 settings at once (9 hidtaiko + 5 extended)
            # 0-3: Sensitivities, 4-8: Delays (ms), 9-13: Double trigger settings
            settings_data = "0:800 1:800 2:800 3:800 4:30 5:30 6:30 7:19 8:25 9:0 10:1200 11:1200 12:1200 13:1200\n"
            print(f"Writing all settings: {settings_data}")
            config.ser.write(settings_data.encode())
            config.ser.flush()
            config.read_response()
        elif command == "set" and len(sys.argv) >= 5:
            key = int(sys.argv[3])
            value = int(sys.argv[4])
            config.set_value(key, value)
        elif command == "stream":
            config.start_streaming()
        elif command == "stream_input":
            config.start_input_streaming()
        elif command == "stopstream":
            config.stop_streaming()
        else:
            print(f"Unknown command: {command}")
            print(__doc__)

        config.close()

    except serial.SerialException as e:
        print(f"Error: {e}")
        print("\nAvailable COM ports:")
        import serial.tools.list_ports
        for port in serial.tools.list_ports.comports():
            print(f"  {port.device}: {port.description}")
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
