import traceback

import cv2
import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QMainWindow, QLabel, QVBoxLayout, \
    QWidget

from src.core.protocol.Keyboard import KeyboardPressPacket, \
    KeyboardReleasePacket
from src.core.protocol.Mouse import MouseMovementAbsolutePercentagePacket, \
    MousePressPacket, MouseReleasePacket, \
    MouseScrollPacket


class MainWindow(QMainWindow):
    def __init__(self, send_to_all_clients_func, stop_running):
        super().__init__()
        self.send_to_all_clients = send_to_all_clients_func
        self.stop_running = stop_running
        self.init_ui()
        self.setMouseTracking(True)
        self.centralWidget().setMouseTracking(True)
        self.image_label.setMouseTracking(True)

    def init_ui(self):
        self.setWindowTitle("Трансляция изображения")
        self.resize(960, 540)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: blue;")

        layout.addWidget(self.image_label)

    def show_img(self, frame: np.ndarray):
        """
        Принимает кадр (OpenCV / NumPy array BGR),
        конвертирует его в формат PyQt и отображает на экране.
        """
        if frame is None:
            return

        try:
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w

            qt_image = QImage(rgb_image.data, w, h, bytes_per_line,
                              QImage.Format_RGB888)

            pixmap = QPixmap.fromImage(qt_image)
            scaled_pixmap = pixmap.scaled(
                self.image_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )

            self.image_label.setPixmap(scaled_pixmap)

        except Exception:
            traceback.print_exc()

    def resizeEvent(self, event):
        """Переопределяем событие изменения размера окна, чтобы картинка не мылилась"""
        self.image_label.resizeEvent(event)

    def mouseMoveEvent(self, event):
        if self.image_label.pixmap() is None:
            return
        x = event.x()-self.width()/2
        y = event.y()-self.height()/2
        x=x/self.image_label.pixmap().width()+0.5
        y=y/self.image_label.pixmap().height()+0.5
        if not (0<=x<=1 and 0<=y<=1):
            return
        self.send_to_all_clients(MouseMovementAbsolutePercentagePacket(x,y))

    def mousePressEvent(self, event):
        self.send_to_all_clients(MousePressPacket(event.button()))

    def mouseReleaseEvent(self, event):
        self.send_to_all_clients(MouseReleasePacket(event.button()))

    def keyPressEvent(self, event):
        self.send_to_all_clients(KeyboardPressPacket(event.nativeScanCode()))

    def keyReleaseEvent(self, event):
        self.send_to_all_clients(KeyboardReleasePacket(event.nativeScanCode()))

    def wheelEvent(self, event):
        self.send_to_all_clients(MouseScrollPacket(event.angleDelta().x(), event.angleDelta().y()))

    def closeEvent(self, event):
        self.stop_running()