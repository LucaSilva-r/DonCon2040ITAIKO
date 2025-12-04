
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush

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
