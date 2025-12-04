
import serial
import time

class SerialConfigHelper:
    """Helper class for DonCon2040 serial configuration protocol"""

    def __init__(self, serial_port):
        self.ser = serial_port

    def send_command(self, command):
        """Send a command code"""
        self.ser.write(f"{command}\n".encode())
        self.ser.flush()

    def read_all_settings(self):
        """Read all settings from device (sends 1000)"""
        # Clear any pending data
        self.ser.reset_input_buffer()

        self.send_command(1000)
        time.sleep(0.3)  # Wait for response

        settings = {}
        while self.ser.in_waiting:
            line = self.ser.readline().decode().strip()
            if ':' in line:
                try:
                    key, value = line.split(':')
                    settings[int(key)] = int(value)
                except ValueError:
                    continue

        return settings

    def write_settings(self, settings_dict):
        """Write settings to device (sends 1002 + key:value pairs)"""
        self.send_command(1002)  # Enter write mode
        time.sleep(0.1)

        # Send all 18 settings space-separated (14 basic + 4 cutoff thresholds)
        settings_str = ' '.join([f"{k}:{v}" for k, v in sorted(settings_dict.items())])
        self.ser.write(f"{settings_str}\n".encode())
        self.ser.flush()
        time.sleep(0.1)

    def save_to_flash(self):
        """Save settings to flash (sends 1001)"""
        self.send_command(1001)
        time.sleep(0.5)

    def start_streaming(self):
        """Start sensor data streaming (sends 2000)"""
        self.send_command(2000)
        time.sleep(0.1)

    def stop_streaming(self):
        """Stop sensor data streaming (sends 2001)"""
        self.send_command(2001)
        time.sleep(0.1)
