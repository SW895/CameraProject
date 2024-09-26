import sys
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QGridLayout,
    QMainWindow,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
)
from PyQt6.QtCore import (
    QThread,
    pyqtSlot,
    Qt,
)
from PyQt6.QtGui import (
    QPixmap,
    QImage
)


class Worker:

    def __init__(self, camera_name, main_window):
        self.camera_name = camera_name
        self.main_window = main_window

    def init_buttons(self):
        self.detection_button = QPushButton('Enable Detection')
        self.detection_button.clicked.connect(
            self.main_window.change_detection_policy
        )
        self.start_recording_button = QPushButton('Start Recording')
        self.start_recording_button.clicked.connect(
            self.main_window.start_video_recording
        )
        self.stop_recording_button = QPushButton('Stop Recording')
        self.stop_recording_button.clicked.connect(
            self.main_window.stop_video_recording
        )
        return [
            self.detection_button,
            self.start_recording_button,
            self.stop_recording_button
        ]

    def init_label(self, widget):
        self.label = QLabel(widget)
        self.label.setPixmap(
            QPixmap(f'{BASE_DIR}/test.jpg').scaled(QT_VIDEO_WIDTH,
                                                   QT_VIDEO_HEIGHT)
        )

    def init_thread(self):
        self.worker = CameraWorker(
            camera_name=self.camera_name,
            camera_source=CAMERA_LIST[self.camera_name]
        )
        self.thread = QThread(self.main_window)
        self.worker.moveToThread(self.thread)
        self.worker.finished.connect(self.thread.quit)
        self.thread.started.connect(self.worker.run_camera)
        #self.thread.finished.connect(app.exit)
        self.worker.changePixmap.connect(self.main_window.setFrame)

    def set_loop(self, loop):
        self.worker.set_loop(loop)

    def init_worker(self):
        self.worker.init_worker()

    def start_worker(self):
        self.thread.start()