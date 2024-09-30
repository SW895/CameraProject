from camera_worker import CameraWorker
from PyQt6.QtWidgets import (
    QLabel,
    QPushButton,
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import QThread
from settings import (
    CAMERA_LIST,
    BASE_DIR,
    QT_VIDEO_WIDTH,
    QT_VIDEO_HEIGHT
)


class Camera:

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
        self.stop_recording_button.setEnabled(False)
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
        return self.label

    def init_thread(self):
        self.worker = CameraWorker(
            camera_name=self.camera_name,
            camera_source=CAMERA_LIST[self.camera_name]
        )
        self.thread = QThread(self.main_window)
        self.worker.moveToThread(self.thread)

    def connect_signals(self):
        self.worker.finished.connect(self.thread.quit)
        self.thread.started.connect(self.worker.run_camera)
        # self.thread.finished.connect(app.exit)
        self.worker.changePixmap.connect(self.main_window.setFrame)
        self.worker.recorder.thread_ended.connect(
            self.main_window.video_recording_thread_ended
        )

    def run(self, loop):
        self.worker.set_loop(loop)
        self.worker.init_worker()
        self.connect_signals()
        self.thread.start()


def search_worker(attr_name, button, workers):
    for worker in workers.values():
        if button == getattr(worker, attr_name):
            return worker
