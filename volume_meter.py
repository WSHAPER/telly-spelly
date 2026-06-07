from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor, QLinearGradient
import numpy as np
from collections import deque

class VolumeMeter(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 20)
        self.value = 0
        self.peaks = []
        self.gradient = self._create_gradient()

        # Smaller buffer for less lag
        self.buffer_size = 3
        self.value_buffer = deque(maxlen=self.buffer_size)

        # Adjusted sensitivity and response
        self.sensitivity = 0.002
        self.smoothing = 0.5
        self.last_value = 0

    def _create_gradient(self):
        gradient = QLinearGradient(0, 0, self.width(), 0)
        gradient.setColorAt(0.0, QColor(0, 255, 0))    # Green
        gradient.setColorAt(0.5, QColor(255, 255, 0))  # Yellow
        gradient.setColorAt(0.8, QColor(255, 128, 0))  # Orange
        gradient.setColorAt(1.0, QColor(255, 0, 0))    # Red
        return gradient

    def resizeEvent(self, event):
        self.gradient = self._create_gradient()
        super().resizeEvent(event)

    def set_value(self, value):
        # Add value to buffer
        self.value_buffer.append(value)

        # Calculate smoothed value
        if len(self.value_buffer) > 0:
            # Use weighted average favoring recent values (newest = highest weight)
            # Weights: oldest=0.2, middle=0.3, newest=0.5
            base_weights = [0.2, 0.3, 0.5]
            weights = np.array(base_weights[-len(self.value_buffer):])
            weights = weights / weights.sum()  # Normalize weights
            avg_value = np.average(list(self.value_buffer), weights=weights)

            # Scale to 0-1 range based on sensitivity
            target_value = min(1.0, avg_value / self.sensitivity)

            # Smooth transition
            smoothed = (self.smoothing * self.last_value +
                       (1 - self.smoothing) * target_value)

            # Apply slight curve for better visual response
            self.value = np.power(smoothed, 0.9)
            self.last_value = smoothed
        else:
            self.value = 0

        # Update peak (compare processed values, not raw vs processed)
        if not self.peaks or self.value > self.peaks[-1][0]:
            self.peaks.append((self.value, 15))

        # Decay peaks
        new_peaks = []
        for peak, frames in self.peaks:
            if frames > 0:
                decayed_peak = peak * 0.95
                if decayed_peak > 0.01:
                    new_peaks.append((decayed_peak, frames - 1))
        self.peaks = new_peaks

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw background
        painter.fillRect(self.rect(), Qt.GlobalColor.black)

        # Draw meter
        width = self.width() - 4
        height = self.height() - 4
        x = 2
        y = 2

        meter_width = int(width * self.value)
        if meter_width > 0:
            rect = self.rect().adjusted(2, 2, -2, -2)
            rect.setWidth(meter_width)
            painter.fillRect(rect, self.gradient)

        # Draw peak markers
        painter.setPen(Qt.GlobalColor.white)
        for peak, _ in self.peaks:
            peak_x = x + int(width * peak)
            painter.drawLine(peak_x, y, peak_x, y + height)
