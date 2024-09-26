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
from camera_worker import CameraWorker


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
        self.worker.finished.connect(self.thread.quit)
        self.thread.started.connect(self.worker.run_camera)
        # self.thread.finished.connect(app.exit)
        self.worker.changePixmap.connect(self.main_window.setFrame)

    def run(self, loop):
        self.worker.set_loop(loop)
        self.worker.init_worker()
        self.thread.start()


def search_worker(attr_name, button, workers):
    print(workers)
    for worker in workers.values():
        if button == getattr(worker, attr_name):
            return worker


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
        pass

    @pyqtSlot(bool)
    def update_connection_status(self, status):
        if status:
            self.status_bar.showMessage('Connection status: OK')
        else:
            self.status_bar.showMessage('Connection status: NO CONNECTION')

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
            camera.worker.request_change_detection_policy()

    def stop_video_recording(self):
        camera = search_worker(
            'stop_recording_button',
            self.sender(),
            self.workers
        )
        if camera:
            camera.worker.request_change_detection_policy()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec())
