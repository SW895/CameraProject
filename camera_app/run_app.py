import sys
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QGridLayout,
    QMainWindow,
    QLabel,
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
from connection_client import ConnectionClient
from connection_handlers import (
    AproveUserHandler,
    VideoRequestHandler,
    StreamHandler
)
from settings import (
    CAMERA_LIST,
    BASE_DIR,
    QT_VIDEO_WIDTH,
    QT_VIDEO_HEIGHT
)
from camera_widget import (
    Camera,
    search_worker,
)


class MainWindow(QMainWindow):

    workers = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for camera in CAMERA_LIST:
            self.workers.update({camera: Camera(camera, self)})

        self.setWindowTitle('ChikenGun 9000')
        self.setGeometry(100, 100, 900, 900)
        self.init_central_widget()
        self.status_bar = self.statusBar()
        self.status_bar.showMessage('Connection status:')
        self.init_camera_workers()
        self.init_network_thread()

    def init_central_widget(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.central_widget_layout = QGridLayout(self.central_widget)
        self.init_camera_labels()

    def init_camera_labels(self):
        row = 0
        column = 0
        slots = (list(CAMERA_LIST.keys())
                 + [None for i in range(6 - len(CAMERA_LIST) % 3)])
        for camera in slots:
            cellWidget = QWidget(self.central_widget)
            cellWidgetLayout = QVBoxLayout(cellWidget)
            buttonsWidget = QWidget()
            buttonsWidgetLayout = QHBoxLayout(buttonsWidget)
            if camera:
                for button in self.workers[camera].init_buttons():
                    buttonsWidgetLayout.addWidget(button)

                label = self.workers[camera].init_label(cellWidget)
            else:
                label = QLabel(cellWidget)
                label.setPixmap(
                    QPixmap(f'{BASE_DIR}/test.jpg').scaled(QT_VIDEO_WIDTH,
                                                           QT_VIDEO_HEIGHT)
                )
            cellWidgetLayout.addWidget(label)
            cellWidgetLayout.addWidget(buttonsWidget)
            cellWidgetLayout.addStretch()
            self.central_widget_layout.addWidget(
                cellWidget,
                row,
                column,
                alignment=Qt.AlignmentFlag.AlignCenter
            )
            column += 1
            if column >= 3:
                column = 0
                row += 1

    def init_camera_workers(self):
        for camera in CAMERA_LIST:
            self.workers[camera].init_thread()

    def init_network_thread(self):
        self.client = ConnectionClient(
            camera_workers_list={
                camera.camera_name: camera.worker
                for camera in list(self.workers.values())
            }
        )
        self.client.add_handlers(
            AproveUserHandler,
            VideoRequestHandler,
            StreamHandler
        )
        self.network_thread = QThread(self)
        self.client.moveToThread(self.network_thread)
        self.client.finished.connect(self.network_thread.quit)
        self.network_thread.started.connect(self.client.run_client)
        self.network_thread.finished.connect(app.exit)
        self.client.connection_status.connect(self.update_connection_status)
        self.client.event_loop_created.connect(self.event_loop_created)
        self.network_thread.start()

    @pyqtSlot()
    def event_loop_created(self):
        for worker in self.workers:
            self.workers[worker].run(self.client.loop)
        self.show()

    @pyqtSlot(QImage, str)
    def setFrame(self, frame, camera_name):
        self.workers[camera_name].label.setPixmap(QPixmap.fromImage(frame))

    @pyqtSlot(bool)
    def update_connection_status(self, status):
        if status:
            self.status_bar.showMessage('Connection status: OK')
        else:
            self.status_bar.showMessage('Connection status: NO CONNECTION')

    @pyqtSlot(str)
    def video_recording_thread_ended(self, camera_name):
        self.workers[camera_name].start_recording_button.setEnabled(True)

    def change_detection_policy(self):
        camera = search_worker('detection_button', self.sender(), self.workers)
        if camera:
            camera.worker.request_change_detection_policy()

    def start_video_recording(self):
        camera = search_worker(
            'start_recording_button',
            self.sender(),
            self.workers
        )
        if camera:
            camera.worker.start_video_recording()
            camera.start_recording_button.setEnabled(False)
            camera.stop_recording_button.setEnabled(True)

    def stop_video_recording(self):
        camera = search_worker(
            'stop_recording_button',
            self.sender(),
            self.workers
        )
        if camera:
            camera.worker.stop_video_recording()
            camera.stop_recording_button.setEnabled(False)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec())
