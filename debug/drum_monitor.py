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
                             QSpinBox, QCheckBox, QGroupBox, QMessageBox,
                             QTabWidget, QFormLayout, QGridLayout)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont, QPainter, QColor, QPen, QBrush
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

        # Send all 14 settings space-separated
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


class DrumVisualWidget(QWidget):
    """Custom widget that draws a visual representation of the Taiko drum"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(600, 600)
        self.setMaximumSize(800, 800)

        # Current trigger states for each pad
        self.triggered = [False, False, False, False]  # Ka_L, Don_L, Don_R, Ka_R

        # Colors matching real Taiko no Tatsujin
        self.colors = {
            'ka_left': QColor(107, 189, 198),      # Katsu cyan (active)
            'don_left': QColor(255, 66, 33),       # Don red (active)
            'don_right': QColor(255, 66, 33),      # Don red (active)
            'ka_right': QColor(107, 189, 198)      # Katsu cyan (active)
        }

        # Dim colors for non-triggered state (darkened by ~70%)
        self.dim_colors = {
            'ka_left': QColor(32, 57, 59),         # Katsu cyan (dim)
            'don_left': QColor(77, 20, 10),        # Don red (dim)
            'don_right': QColor(77, 20, 10),       # Don red (dim)
            'ka_right': QColor(32, 57, 59)         # Katsu cyan (dim)
        }

    def set_trigger_states(self, ka_left, don_left, don_right, ka_right):
        """Update trigger states and redraw"""
        self.triggered = [ka_left, don_left, don_right, ka_right]
        self.update()  # Trigger a repaint

    def paintEvent(self, event):
        """Draw the drum"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Get widget dimensions
        width = self.width()
        height = self.height()
        center_x = width // 2
        center_y = height // 2

        # Calculate drum dimensions (leave more margin for labels)
        drum_radius = min(width, height) // 2 - 100
        face_radius = int(drum_radius * 0.7)
        rim_width = drum_radius - face_radius

        # Draw rim sections (Ka pads)
        # Left rim (Ka Left)
        color_ka_left = self.colors['ka_left'] if self.triggered[0] else self.dim_colors['ka_left']
        painter.setBrush(QBrush(color_ka_left))
        painter.setPen(QPen(QColor(50, 50, 50), 3))
        painter.drawPie(center_x - drum_radius, center_y - drum_radius,
                       drum_radius * 2, drum_radius * 2,
                       90 * 16, 180 * 16)  # Left half (90° to 270°)

        # Right rim (Ka Right)
        color_ka_right = self.colors['ka_right'] if self.triggered[3] else self.dim_colors['ka_right']
        painter.setBrush(QBrush(color_ka_right))
        painter.drawPie(center_x - drum_radius, center_y - drum_radius,
                       drum_radius * 2, drum_radius * 2,
                       270 * 16, 180 * 16)  # Right half (270° to 90°)

        # Draw face sections (Don pads) - split vertically
        # Left face (Don Left)
        color_don_left = self.colors['don_left'] if self.triggered[1] else self.dim_colors['don_left']
        painter.setBrush(QBrush(color_don_left))
        painter.setPen(QPen(QColor(50, 50, 50), 3))
        painter.drawPie(center_x - face_radius, center_y - face_radius,
                       face_radius * 2, face_radius * 2,
                       90 * 16, 180 * 16)  # Left half

        # Right face (Don Right)
        color_don_right = self.colors['don_right'] if self.triggered[2] else self.dim_colors['don_right']
        painter.setBrush(QBrush(color_don_right))
        painter.drawPie(center_x - face_radius, center_y - face_radius,
                       face_radius * 2, face_radius * 2,
                       270 * 16, 180 * 16)  # Right half

        # Draw center dividing line
        painter.setPen(QPen(QColor(50, 50, 50), 4))
        painter.drawLine(center_x, center_y - face_radius, center_x, center_y + face_radius)

        # Draw labels with better positioning
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        font = painter.font()
        font.setPointSize(12)
        font.setBold(True)
        painter.setFont(font)

        # Ka Left label (positioned to the left of the drum)
        ka_left_text = "Ka Left (Rim)"
        painter.drawText(20, center_y + 5, ka_left_text)

        # Ka Right label (positioned to the right of the drum)
        ka_right_text = "Ka Right (Rim)"
        text_width = painter.fontMetrics().horizontalAdvance(ka_right_text)
        painter.drawText(width - text_width - 20, center_y + 5, ka_right_text)

        # Don Left label (on the left face)
        don_left_text = "Don Left"
        painter.drawText(center_x - face_radius // 2 - 35, center_y + 5, don_left_text)

        # Don Right label (on the right face)
        don_right_text = "Don Right"
        painter.drawText(center_x + 15, center_y + 5, don_right_text)


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
        self.config_helper = None
        self.is_running = False
        self.is_streaming = False
        self.log_file = None
        self.csv_writer = None

        # Data buffers (store last N points)
        self.buffer_size = 10000
        self.time_data = deque(maxlen=self.buffer_size)
        self.pad_data = [deque(maxlen=self.buffer_size) for _ in range(4)]
        self.trigger_data = [deque(maxlen=self.buffer_size) for _ in range(4)]
        self.delta_data = [deque(maxlen=self.buffer_size) for _ in range(4)]  # Delta values
        self.trigger_duration_data = [deque(maxlen=self.buffer_size) for _ in range(4)]  # Trigger duration

        # Track last raw values for delta calculation
        self.last_raw_values = [0, 0, 0, 0]

        # Thresholds for visual reference (can be adjusted in UI)
        self.thresholds = [450, 350, 350, 450]  # Ka_L, Don_L, Don_R, Ka_R
        self.heavy_thresholds = [900, 700, 700, 900]  # Ka_L, Don_L, Don_R, Ka_R (heavy/double trigger)

        # Configuration widgets (created in create_config_panel)
        self.config_widgets = {}

        self.time_counter = 0
        self.plot_update_counter = 0

        self.init_ui()
        self.setup_plots()

        # Fast timer for reading serial data and updating visual drum (10ms)
        self.data_timer = QTimer()
        self.data_timer.timeout.connect(self.update_data)

        # Separate slower timer for plot updates (configurable)
        self.plot_timer = QTimer()
        self.plot_timer.timeout.connect(self.update_plots)

    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("DonCon2040 Drum Monitor & Configurator")
        self.setGeometry(100, 100, 1400, 900)

        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Control panel (port selection, connect button)
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel)

        # Tab widget for Monitor and Configuration
        self.tab_widget = QTabWidget()
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        main_layout.addWidget(self.tab_widget)

        # Create Live Monitor tab
        monitor_tab = QWidget()
        monitor_layout = QVBoxLayout(monitor_tab)

        # Monitor controls (update rate, buffer size, logging)
        monitor_controls = self.create_monitor_controls()
        monitor_layout.addWidget(monitor_controls)

        # Graphics layout for plots
        self.graphics_layout = pg.GraphicsLayoutWidget()
        monitor_layout.addWidget(self.graphics_layout)

        self.tab_widget.addTab(monitor_tab, "Live Monitor")

        # Create Configuration tab
        config_tab = self.create_config_panel()
        self.tab_widget.addTab(config_tab, "Configuration")

        # Create Visual Drum tab
        visual_tab = QWidget()
        visual_layout = QVBoxLayout(visual_tab)

        # Add the drum visual widget (centered at top)
        self.drum_visual = DrumVisualWidget()
        visual_layout.addWidget(self.drum_visual, alignment=Qt.AlignHCenter | Qt.AlignTop)

        # Add stretch to push drum to top
        visual_layout.addStretch()

        self.tab_widget.addTab(visual_tab, "Visual Drum")

        # Status bar
        self.statusBar().showMessage("Disconnected")

    def create_control_panel(self):
        """Create the connection control panel"""
        group = QGroupBox("Connection")
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

        layout.addStretch()

        group.setLayout(layout)
        return group

    def create_monitor_controls(self):
        """Create monitor-specific controls"""
        group = QGroupBox("Monitor Controls")
        layout = QHBoxLayout()

        # Update rate control (only affects plots, not visual drum)
        layout.addWidget(QLabel("Plot Refresh (ms):"))
        self.update_rate_spin = QSpinBox()
        self.update_rate_spin.setRange(10, 1000)
        self.update_rate_spin.setValue(50)
        self.update_rate_spin.valueChanged.connect(self.on_plot_rate_changed)
        self.update_rate_spin.setToolTip("How often graphs refresh (higher = smoother, visual drum always fast)")
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

    def create_config_panel(self):
        """Create the configuration panel"""
        widget = QWidget()
        main_layout = QVBoxLayout(widget)

        # Basic Thresholds section
        threshold_group = QGroupBox("Basic Thresholds (Trigger Sensitivity)")
        threshold_layout = QFormLayout()

        self.config_widgets[0] = QSpinBox()  # Don Left
        self.config_widgets[0].setRange(0, 4095)
        self.config_widgets[0].setValue(800)
        threshold_layout.addRow("Don Left (Left Face):", self.config_widgets[0])

        self.config_widgets[1] = QSpinBox()  # Ka Left
        self.config_widgets[1].setRange(0, 4095)
        self.config_widgets[1].setValue(800)
        threshold_layout.addRow("Ka Left (Left Rim):", self.config_widgets[1])

        self.config_widgets[2] = QSpinBox()  # Don Right
        self.config_widgets[2].setRange(0, 4095)
        self.config_widgets[2].setValue(800)
        threshold_layout.addRow("Don Right (Right Face):", self.config_widgets[2])

        self.config_widgets[3] = QSpinBox()  # Ka Right
        self.config_widgets[3].setRange(0, 4095)
        self.config_widgets[3].setValue(800)
        threshold_layout.addRow("Ka Right (Right Rim):", self.config_widgets[3])

        threshold_group.setLayout(threshold_layout)
        main_layout.addWidget(threshold_group)

        # Timing Settings section
        timing_group = QGroupBox("Timing Settings (milliseconds)")
        timing_layout = QFormLayout()

        self.config_widgets[4] = QSpinBox()  # Don Debounce
        self.config_widgets[4].setRange(0, 1000)
        self.config_widgets[4].setValue(30)
        timing_layout.addRow("Don Debounce (B delay):", self.config_widgets[4])

        self.config_widgets[5] = QSpinBox()  # Kat Debounce
        self.config_widgets[5].setRange(0, 1000)
        self.config_widgets[5].setValue(30)
        timing_layout.addRow("Kat Debounce (C delay):", self.config_widgets[5])

        self.config_widgets[6] = QSpinBox()  # Crosstalk Debounce
        self.config_widgets[6].setRange(0, 1000)
        self.config_widgets[6].setValue(30)
        timing_layout.addRow("Crosstalk Debounce (D delay):", self.config_widgets[6])

        self.config_widgets[7] = QSpinBox()  # Key Timeout
        self.config_widgets[7].setRange(0, 1000)
        self.config_widgets[7].setValue(19)
        timing_layout.addRow("Key Timeout (H delay):", self.config_widgets[7])

        self.config_widgets[8] = QSpinBox()  # Debounce Delay
        self.config_widgets[8].setRange(0, 1000)
        self.config_widgets[8].setValue(25)
        timing_layout.addRow("Debounce Delay (A delay):", self.config_widgets[8])

        timing_group.setLayout(timing_layout)
        main_layout.addWidget(timing_group)

        # Double Trigger Settings section
        double_group = QGroupBox("Double Trigger Settings")
        double_layout = QFormLayout()

        self.config_widgets[9] = QComboBox()  # Double Trigger Mode
        self.config_widgets[9].addItems(["Off", "Threshold"])
        self.config_widgets[9].setCurrentIndex(0)
        self.config_widgets[9].currentIndexChanged.connect(self.on_double_mode_changed)
        double_layout.addRow("Double Trigger Mode:", self.config_widgets[9])

        self.config_widgets[10] = QSpinBox()  # Double Don Left
        self.config_widgets[10].setRange(0, 4095)
        self.config_widgets[10].setValue(1200)
        self.config_widgets[10].setEnabled(False)
        double_layout.addRow("Double Don Left:", self.config_widgets[10])

        self.config_widgets[11] = QSpinBox()  # Double Ka Left
        self.config_widgets[11].setRange(0, 4095)
        self.config_widgets[11].setValue(1200)
        self.config_widgets[11].setEnabled(False)
        double_layout.addRow("Double Ka Left:", self.config_widgets[11])

        self.config_widgets[12] = QSpinBox()  # Double Don Right
        self.config_widgets[12].setRange(0, 4095)
        self.config_widgets[12].setValue(1200)
        self.config_widgets[12].setEnabled(False)
        double_layout.addRow("Double Don Right:", self.config_widgets[12])

        self.config_widgets[13] = QSpinBox()  # Double Ka Right
        self.config_widgets[13].setRange(0, 4095)
        self.config_widgets[13].setValue(1200)
        self.config_widgets[13].setEnabled(False)
        double_layout.addRow("Double Ka Right:", self.config_widgets[13])

        double_group.setLayout(double_layout)
        main_layout.addWidget(double_group)

        # Action Buttons
        button_layout = QHBoxLayout()

        read_btn = QPushButton("Read from Device")
        read_btn.clicked.connect(self.read_config_from_device)
        button_layout.addWidget(read_btn)

        write_btn = QPushButton("Write to Device && Save")
        write_btn.clicked.connect(self.write_config_to_device)
        button_layout.addWidget(write_btn)

        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self.reset_config_to_defaults)
        button_layout.addWidget(reset_btn)

        button_layout.addStretch()

        main_layout.addLayout(button_layout)
        main_layout.addStretch()

        return widget

    def setup_plots(self):
        """Setup the plot widgets"""
        self.plots = []
        self.curves = []
        self.delta_curves = []
        self.trigger_duration_curves = []
        self.threshold_lines = []
        self.heavy_threshold_lines = []

        for i, (name, color) in enumerate(self.PADS):
            # Create plot
            plot = self.graphics_layout.addPlot(row=i, col=0)
            plot.setLabel('left', 'ADC Value / Delta')
            plot.setLabel('bottom', 'Time (samples)')
            plot.setTitle(name, color=color)
            plot.showGrid(x=True, y=True, alpha=0.3)
            plot.setYRange(0, 4096)

            # Create curve for raw ADC values
            curve = plot.plot(pen=pg.mkPen(color=color, width=2))

            # Create curve for delta values (difference from last sample)
            delta_color = (color[0] // 2 + 127, color[1] // 2 + 127, color[2] // 2 + 127)  # Lighter version
            delta_curve = plot.plot(pen=pg.mkPen(color=delta_color, width=1, style=Qt.DotLine))

            # Create curve for trigger duration (how long the trigger has been held)
            duration_color = (255, 255, 255)  # White for visibility
            trigger_duration_curve = plot.plot(pen=pg.mkPen(color=duration_color, width=3, style=Qt.SolidLine))

            # Add light threshold line (yellow)
            threshold_line = pg.InfiniteLine(
                pos=self.thresholds[i],
                angle=0,
                pen=pg.mkPen(color=(255, 255, 0), width=2, style=Qt.DashLine),
                label=f'Light: {self.thresholds[i]}'
            )
            plot.addItem(threshold_line)

            # Add heavy threshold line (orange)
            heavy_threshold_line = pg.InfiniteLine(
                pos=self.heavy_thresholds[i],
                angle=0,
                pen=pg.mkPen(color=(255, 165, 0), width=2, style=Qt.DashLine),
                label=f'Heavy: {self.heavy_thresholds[i]}'
            )
            plot.addItem(heavy_threshold_line)

            # Add legend
            plot.addLegend()
            plot.legend.addItem(curve, "Raw ADC")
            plot.legend.addItem(delta_curve, "Delta (trigger logic)")
            plot.legend.addItem(trigger_duration_curve, "Trigger Duration (ms)")

            self.plots.append(plot)
            self.curves.append(curve)
            self.delta_curves.append(delta_curve)
            self.trigger_duration_curves.append(trigger_duration_curve)
            self.threshold_lines.append(threshold_line)
            self.heavy_threshold_lines.append(heavy_threshold_line)

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
            self.config_helper = SerialConfigHelper(self.serial_port)
            self.is_running = True
            self.connect_btn.setText("Disconnect")
            self.connect_btn.setStyleSheet("background-color: #ff4444")
            self.port_combo.setEnabled(False)

            # Start streaming if on Live Monitor tab or Visual Drum tab
            if self.tab_widget.currentIndex() == 0 or self.tab_widget.currentIndex() == 2:
                self.config_helper.start_streaming()
                self.is_streaming = True

            # Start fast data timer (always 10ms for responsiveness)
            self.data_timer.start(10)

            # Start plot update timer (user configurable, default 10ms)
            plot_rate = self.update_rate_spin.value()
            self.plot_timer.start(plot_rate)

            self.statusBar().showMessage(f"Connected to {port}")

            # Automatically read config on connect
            self.read_config_from_device()

        except serial.SerialException as e:
            QMessageBox.critical(self, "Connection Error", f"Failed to open port:\n{e}")

    def disconnect(self):
        """Disconnect from serial port"""
        # Stop streaming if active
        if self.config_helper and self.is_streaming:
            try:
                self.config_helper.stop_streaming()
            except serial.SerialException:
                # Ignore error if device is already gone
                pass
            self.is_streaming = False

        self.is_running = False
        self.data_timer.stop()
        self.plot_timer.stop()

        if self.serial_port:
            self.serial_port.close()
            self.serial_port = None

        self.config_helper = None

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

    def on_plot_rate_changed(self, value):
        """Update plot timer interval when user changes the refresh rate"""
        if self.is_running:
            self.plot_timer.setInterval(value)

    def update_buffer_size(self, new_size):
        """Update the buffer size for data history"""
        self.buffer_size = new_size
        self.time_data = deque(self.time_data, maxlen=new_size)
        for i in range(4):
            self.pad_data[i] = deque(self.pad_data[i], maxlen=new_size)
            self.trigger_data[i] = deque(self.trigger_data[i], maxlen=new_size)
            self.delta_data[i] = deque(self.delta_data[i], maxlen=new_size)
            self.trigger_duration_data[i] = deque(self.trigger_duration_data[i], maxlen=new_size)

    def clear_data(self):
        """Clear all data buffers"""
        self.time_data.clear()
        for i in range(4):
            self.pad_data[i].clear()
            self.trigger_data[i].clear()
            self.delta_data[i].clear()
            self.trigger_duration_data[i].clear()
        self.last_raw_values = [0, 0, 0, 0]
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

                # Skip library error messages (e.g., "[ssd1306_write] addr not acknowledged!")
                if line.startswith('['):
                    continue

                # Parse CSV format: T/F,raw,duration,T/F,raw,duration,T/F,raw,duration,T/F,raw,duration
                parts = line.split(',')

                if len(parts) != 12:
                    continue  # Skip malformed lines

                # Parse triggered states, raw values, and durations
                try:
                    triggered = [parts[i] == 'T' for i in range(0, 12, 3)]
                    raw_values = [int(parts[i]) for i in range(1, 12, 3)]
                    trigger_durations = [int(parts[i]) for i in range(2, 12, 3)]
                except (ValueError, IndexError):
                    continue  # Skip if parsing fails

                # Calculate delta values (what the algorithm actually uses)
                delta_values = []
                for i in range(4):
                    delta = raw_values[i] - self.last_raw_values[i]
                    delta_values.append(max(0, delta))  # Clamp negative deltas to 0 for visualization
                    self.last_raw_values[i] = raw_values[i]

                # Trigger durations are now provided by firmware (already parsed above)

                # Add to buffers
                self.time_data.append(self.time_counter)
                for i in range(4):
                    self.pad_data[i].append(raw_values[i])
                    self.trigger_data[i].append(triggered[i])
                    self.delta_data[i].append(delta_values[i])
                    self.trigger_duration_data[i].append(trigger_durations[i])

                self.time_counter += 1

                # Update visual drum with current trigger states
                # triggered order is: Ka_L, Don_L, Don_R, Ka_R
                self.drum_visual.set_trigger_states(
                    triggered[0],  # Ka Left
                    triggered[1],  # Don Left
                    triggered[2],  # Don Right
                    triggered[3]   # Ka Right
                )

                # Log to CSV if enabled
                if self.csv_writer:
                    self.csv_writer.writerow([
                        datetime.now().isoformat(),
                        *[f"{parts[i]},{parts[i+1]}" for i in range(0, 8, 2)]
                    ])

        except serial.SerialException as e:
            self.disconnect()

    def update_plots(self):
        """Update all plot curves with current data"""
        # Only update if on Live Monitor tab (performance optimization)
        if self.tab_widget.currentIndex() != 0:
            return

        if len(self.time_data) == 0:
            return

        time_array = list(self.time_data)

        for i in range(4):
            if len(self.pad_data[i]) > 0:
                # Update raw ADC curve
                self.curves[i].setData(time_array, list(self.pad_data[i]))

                # Update delta curve
                self.delta_curves[i].setData(time_array, list(self.delta_data[i]))

                # Update trigger duration curve
                self.trigger_duration_curves[i].setData(time_array, list(self.trigger_duration_data[i]))

                # Update plot line width if triggered (make it thicker/more visible)
                color = self.PADS[i][1]
                if self.trigger_data[i][-1]:  # Last value is triggered
                    # Brighter and thicker when triggered
                    self.curves[i].setPen(pg.mkPen(color=color, width=4))
                else:
                    # Normal width when not triggered
                    self.curves[i].setPen(pg.mkPen(color=color, width=2))

    def on_tab_changed(self, index):
        """Handle tab change - start/stop streaming"""
        if not self.is_running:
            return

        if index == 0 or index == 2:  # Live Monitor tab or Visual Drum tab
            # Start streaming
            if self.config_helper and not self.is_streaming:
                self.config_helper.start_streaming()
                self.is_streaming = True
                self.statusBar().showMessage("Streaming sensor data...")
        else:  # Configuration tab
            # Stop streaming
            if self.config_helper and self.is_streaming:
                self.config_helper.stop_streaming()
                self.is_streaming = False
                self.statusBar().showMessage("Streaming stopped (Configuration mode)")

    def on_double_mode_changed(self, index):
        """Enable/disable double trigger threshold spinboxes based on mode"""
        # Enable thresholds only when mode is "Threshold" (index 1)
        enabled = (index == 1)
        self.config_widgets[10].setEnabled(enabled)
        self.config_widgets[11].setEnabled(enabled)
        self.config_widgets[12].setEnabled(enabled)
        self.config_widgets[13].setEnabled(enabled)

    def read_config_from_device(self):
        """Read configuration from device and update UI"""
        if not self.config_helper:
            QMessageBox.warning(self, "Not Connected", "Please connect to device first")
            return

        try:
            settings = self.config_helper.read_all_settings()

            if not settings:
                QMessageBox.warning(self, "Read Failed", "No settings received from device")
                return

            # Update spinboxes with received values
            for key, value in settings.items():
                if key in self.config_widgets:
                    if key == 9:  # Double trigger mode (dropdown)
                        self.config_widgets[key].setCurrentIndex(value)
                    else:  # Spinboxes
                        self.config_widgets[key].setValue(value)

            # Update light threshold lines on graphs
            if 0 in settings and 1 in settings and 2 in settings and 3 in settings:
                self.thresholds = [settings[1], settings[0], settings[2], settings[3]]  # Ka_L, Don_L, Don_R, Ka_R
                for i, threshold_line in enumerate(self.threshold_lines):
                    threshold_line.setValue(self.thresholds[i])
                    threshold_line.label.setFormat(f'Light: {self.thresholds[i]}')

            # Update heavy threshold lines on graphs
            if 10 in settings and 11 in settings and 12 in settings and 13 in settings:
                self.heavy_thresholds = [settings[11], settings[10], settings[12], settings[13]]  # Ka_L, Don_L, Don_R, Ka_R
                for i, heavy_threshold_line in enumerate(self.heavy_threshold_lines):
                    heavy_threshold_line.setValue(self.heavy_thresholds[i])
                    heavy_threshold_line.label.setFormat(f'Heavy: {self.heavy_thresholds[i]}')

            self.statusBar().showMessage(f"Read {len(settings)} settings from device")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to read settings:\n{e}")

    def write_config_to_device(self):
        """Write configuration to device"""
        if not self.config_helper:
            QMessageBox.warning(self, "Not Connected", "Please connect to device first")
            return

        try:
            # Collect all settings from UI
            settings = {}
            for key in range(14):
                if key == 9:  # Double trigger mode (dropdown)
                    settings[key] = self.config_widgets[key].currentIndex()
                else:  # Spinboxes
                    settings[key] = self.config_widgets[key].value()

            self.config_helper.write_settings(settings)

            # Update light threshold lines on graphs
            self.thresholds = [settings[1], settings[0], settings[2], settings[3]]  # Ka_L, Don_L, Don_R, Ka_R
            for i, threshold_line in enumerate(self.threshold_lines):
                threshold_line.setValue(self.thresholds[i])
                threshold_line.label.setFormat(f'Light: {self.thresholds[i]}')

            # Update heavy threshold lines on graphs
            self.heavy_thresholds = [settings[11], settings[10], settings[12], settings[13]]  # Ka_L, Don_L, Don_R, Ka_R
            for i, heavy_threshold_line in enumerate(self.heavy_threshold_lines):
                heavy_threshold_line.setValue(self.heavy_thresholds[i])
                heavy_threshold_line.label.setFormat(f'Heavy: {self.heavy_thresholds[i]}')

            # Automatically save to flash after writing
            self.config_helper.save_to_flash()

            self.statusBar().showMessage("Settings written to device and saved to flash memory")
            QMessageBox.information(self, "Success", "Settings written to device and saved to flash memory")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to write settings:\n{e}")

    def save_config_to_flash(self):
        """Save current settings to flash memory"""
        if not self.config_helper:
            QMessageBox.warning(self, "Not Connected", "Please connect to device first")
            return

        try:
            self.config_helper.save_to_flash()
            QMessageBox.information(self, "Saved", "Settings saved to flash memory")
            self.statusBar().showMessage("Settings saved to flash memory")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save to flash:\n{e}")

    def reset_config_to_defaults(self):
        """Reset configuration UI to default values"""
        defaults = {
            0: 800, 1: 800, 2: 800, 3: 800,  # Thresholds
            4: 30, 5: 30, 6: 30, 7: 19, 8: 25,  # Timing
            9: 0,  # Double trigger mode (Off)
            10: 1200, 11: 1200, 12: 1200, 13: 1200  # Double thresholds
        }

        for key, value in defaults.items():
            if key == 9:  # Double trigger mode (dropdown)
                self.config_widgets[key].setCurrentIndex(value)
            else:  # Spinboxes
                self.config_widgets[key].setValue(value)

        self.statusBar().showMessage("Configuration reset to defaults (not written to device)")

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
