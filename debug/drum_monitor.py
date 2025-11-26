#!/usr/bin/env python3
"""
DonCon2040 Drum Monitor - Real-time ADC visualization tool
Displays live graphs of drum pad sensor values and trigger states
"""

import sys
import serial
import serial.tools.list_ports
from collections import deque
from datetime import datetime
import csv

import pyqtgraph as pg
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QComboBox, QLabel,
                             QSpinBox, QCheckBox, QGroupBox, QMessageBox)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont


class DrumMonitor(QMainWindow):
    """Main application window for drum monitoring"""

    # Pad names and colors
    PADS = [
        ("Ka Left", (255, 100, 100)),    # Red
        ("Don Left", (100, 100, 255)),   # Blue
        ("Don Right", (100, 255, 100)),  # Green
        ("Ka Right", (255, 200, 100))    # Orange
    ]

    def __init__(self):
        super().__init__()
        self.serial_port = None
        self.is_running = False
        self.log_file = None
        self.csv_writer = None

        # Data buffers (store last N points)
        self.buffer_size = 1000
        self.time_data = deque(maxlen=self.buffer_size)
        self.pad_data = [deque(maxlen=self.buffer_size) for _ in range(4)]
        self.trigger_data = [deque(maxlen=self.buffer_size) for _ in range(4)]

        # Thresholds for visual reference (can be adjusted in UI)
        self.thresholds = [450, 350, 350, 450]  # Ka_L, Don_L, Don_R, Ka_R

        self.time_counter = 0

        self.init_ui()
        self.setup_plots()

        # Timer for reading serial data
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)

    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("DonCon2040 Drum Monitor")
        self.setGeometry(100, 100, 1400, 900)

        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Control panel
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel)

        # Graphics layout for plots
        self.graphics_layout = pg.GraphicsLayoutWidget()
        main_layout.addWidget(self.graphics_layout)

        # Status bar
        self.statusBar().showMessage("Disconnected")

    def create_control_panel(self):
        """Create the control panel with buttons and settings"""
        group = QGroupBox("Controls")
        layout = QHBoxLayout()

        # Serial port selection
        layout.addWidget(QLabel("Port:"))
        self.port_combo = QComboBox()
        self.refresh_ports()
        layout.addWidget(self.port_combo)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_ports)
        layout.addWidget(refresh_btn)

        # Connect/Disconnect button
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.toggle_connection)
        layout.addWidget(self.connect_btn)

        layout.addWidget(QLabel("|"))

        # Update rate control
        layout.addWidget(QLabel("Update Rate (ms):"))
        self.update_rate_spin = QSpinBox()
        self.update_rate_spin.setRange(1, 1000)
        self.update_rate_spin.setValue(10)
        self.update_rate_spin.setToolTip("Update interval in milliseconds (lower = faster)")
        layout.addWidget(self.update_rate_spin)

        # Buffer size control
        layout.addWidget(QLabel("History (samples):"))
        self.buffer_spin = QSpinBox()
        self.buffer_spin.setRange(100, 10000)
        self.buffer_spin.setValue(1000)
        self.buffer_spin.valueChanged.connect(self.update_buffer_size)
        layout.addWidget(self.buffer_spin)

        layout.addWidget(QLabel("|"))

        # Data logging
        self.log_checkbox = QCheckBox("Log to CSV")
        self.log_checkbox.stateChanged.connect(self.toggle_logging)
        layout.addWidget(self.log_checkbox)

        # Clear button
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_data)
        layout.addWidget(clear_btn)

        layout.addStretch()

        group.setLayout(layout)
        return group

    def setup_plots(self):
        """Setup the plot widgets"""
        self.plots = []
        self.curves = []
        self.threshold_lines = []

        for i, (name, color) in enumerate(self.PADS):
            # Create plot
            plot = self.graphics_layout.addPlot(row=i, col=0)
            plot.setLabel('left', 'ADC Value')
            plot.setLabel('bottom', 'Time (samples)')
            plot.setTitle(name, color=color)
            plot.showGrid(x=True, y=True, alpha=0.3)
            plot.setYRange(0, 4096)

            # Create curve for ADC values
            curve = plot.plot(pen=pg.mkPen(color=color, width=2))

            # Add threshold line
            threshold_line = pg.InfiniteLine(
                pos=self.thresholds[i],
                angle=0,
                pen=pg.mkPen(color=(255, 255, 0), width=2, style=Qt.DashLine),
                label=f'Threshold: {self.thresholds[i]}'
            )
            plot.addItem(threshold_line)

            self.plots.append(plot)
            self.curves.append(curve)
            self.threshold_lines.append(threshold_line)

    def refresh_ports(self):
        """Refresh the list of available serial ports"""
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()

        for port in ports:
            # Highlight Raspberry Pi Pico ports
            if "2E8A" in port.hwid.upper():  # Raspberry Pi vendor ID
                self.port_combo.addItem(f"{port.device} - DonCon2040", port.device)
            else:
                self.port_combo.addItem(f"{port.device} - {port.description}", port.device)

        if self.port_combo.count() == 0:
            self.port_combo.addItem("No ports found", None)

    def toggle_connection(self):
        """Connect or disconnect from serial port"""
        if not self.is_running:
            self.connect()
        else:
            self.disconnect()

    def connect(self):
        """Connect to the selected serial port"""
        port = self.port_combo.currentData()

        if port is None:
            QMessageBox.warning(self, "Error", "No valid port selected")
            return

        try:
            self.serial_port = serial.Serial(port, baudrate=115200, timeout=0.1)
            self.is_running = True
            self.connect_btn.setText("Disconnect")
            self.connect_btn.setStyleSheet("background-color: #ff4444")
            self.port_combo.setEnabled(False)

            # Start the update timer
            update_rate = self.update_rate_spin.value()
            self.timer.start(update_rate)

            self.statusBar().showMessage(f"Connected to {port}")

        except serial.SerialException as e:
            QMessageBox.critical(self, "Connection Error", f"Failed to open port:\n{e}")

    def disconnect(self):
        """Disconnect from serial port"""
        self.is_running = False
        self.timer.stop()

        if self.serial_port:
            self.serial_port.close()
            self.serial_port = None

        self.connect_btn.setText("Connect")
        self.connect_btn.setStyleSheet("")
        self.port_combo.setEnabled(True)
        self.statusBar().showMessage("Disconnected")

        if self.log_file:
            self.log_file.close()
            self.log_file = None
            self.csv_writer = None

    def toggle_logging(self, state):
        """Enable or disable CSV logging"""
        if state == Qt.Checked and self.is_running:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"drum_log_{timestamp}.csv"
            self.log_file = open(filename, 'w', newline='')
            self.csv_writer = csv.writer(self.log_file)
            self.csv_writer.writerow([
                'timestamp',
                'ka_left_triggered', 'ka_left_raw',
                'don_left_triggered', 'don_left_raw',
                'don_right_triggered', 'don_right_raw',
                'ka_right_triggered', 'ka_right_raw'
            ])
            self.statusBar().showMessage(f"Logging to {filename}")
        elif state == Qt.Unchecked and self.log_file:
            self.log_file.close()
            self.log_file = None
            self.csv_writer = None

    def update_buffer_size(self, new_size):
        """Update the buffer size for data history"""
        self.buffer_size = new_size
        self.time_data = deque(self.time_data, maxlen=new_size)
        for i in range(4):
            self.pad_data[i] = deque(self.pad_data[i], maxlen=new_size)
            self.trigger_data[i] = deque(self.trigger_data[i], maxlen=new_size)

    def clear_data(self):
        """Clear all data buffers"""
        self.time_data.clear()
        for i in range(4):
            self.pad_data[i].clear()
            self.trigger_data[i].clear()
        self.time_counter = 0

    def update_data(self):
        """Read data from serial port and update plots"""
        if not self.serial_port or not self.serial_port.is_open:
            return

        try:
            # Read all available lines
            while self.serial_port.in_waiting:
                line = self.serial_port.readline().decode('utf-8').strip()

                if not line:
                    continue

                # Parse CSV format: T/F,raw,T/F,raw,T/F,raw,T/F,raw
                parts = line.split(',')

                if len(parts) != 8:
                    continue  # Skip malformed lines

                # Parse triggered states and raw values
                try:
                    triggered = [parts[i] == 'T' for i in range(0, 8, 2)]
                    raw_values = [int(parts[i]) for i in range(1, 8, 2)]
                except (ValueError, IndexError):
                    continue  # Skip if parsing fails

                # Add to buffers
                self.time_data.append(self.time_counter)
                for i in range(4):
                    self.pad_data[i].append(raw_values[i])
                    self.trigger_data[i].append(triggered[i])

                self.time_counter += 1

                # Log to CSV if enabled
                if self.csv_writer:
                    self.csv_writer.writerow([
                        datetime.now().isoformat(),
                        *[f"{parts[i]},{parts[i+1]}" for i in range(0, 8, 2)]
                    ])

            # Update plots
            self.update_plots()

        except serial.SerialException as e:
            self.disconnect()
            QMessageBox.critical(self, "Serial Error", f"Lost connection:\n{e}")

    def update_plots(self):
        """Update all plot curves with current data"""
        if len(self.time_data) == 0:
            return

        time_array = list(self.time_data)

        for i in range(4):
            if len(self.pad_data[i]) > 0:
                self.curves[i].setData(time_array, list(self.pad_data[i]))

                # Update plot line width if triggered (make it thicker/more visible)
                color = self.PADS[i][1]
                if self.trigger_data[i][-1]:  # Last value is triggered
                    # Brighter and thicker when triggered
                    self.curves[i].setPen(pg.mkPen(color=color, width=4))
                else:
                    # Normal width when not triggered
                    self.curves[i].setPen(pg.mkPen(color=color, width=2))

    def closeEvent(self, event):
        """Handle window close event"""
        self.disconnect()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Modern look

    # Set dark theme
    app.setStyleSheet("""
        QMainWindow, QWidget {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        QGroupBox {
            border: 1px solid #555555;
            border-radius: 5px;
            margin-top: 10px;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
        }
        QPushButton {
            background-color: #3d3d3d;
            border: 1px solid #555555;
            padding: 5px 15px;
            border-radius: 3px;
        }
        QPushButton:hover {
            background-color: #4d4d4d;
        }
        QPushButton:pressed {
            background-color: #2d2d2d;
        }
        QComboBox, QSpinBox {
            background-color: #3d3d3d;
            border: 1px solid #555555;
            padding: 3px;
            border-radius: 3px;
        }
    """)

    window = DrumMonitor()
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
