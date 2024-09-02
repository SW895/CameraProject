import sys
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QGridLayout,
    QMainWindow,
    QLabel,
    QPushButton
)
from PyQt6.QtCore import (
    QThread,
    pyqtSignal,
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
    CAMERA_LIST
)
from camera_worker import CameraWorker


class MainWindow(QMainWindow):

    camera_labels = {}
    camera_workers = {}
    camera_threads = {}
    buttons = {}
    enable_detection = pyqtSignal()
    disable_detection = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
        for camera in CAMERA_LIST:
            current_label = QLabel(self)
            self.camera_labels.update({camera: current_label})
            self.central_widget_layout.addWidget(
                current_label,
                row,
                column,
                alignment=Qt.AlignmentFlag.AlignCenter
            )

            current_button = QPushButton('Enable Detection')
            self.buttons.update({camera: current_button})
            current_button.setCheckable(True)
            current_button.toggle()
            current_button.clicked.connect(self.enable_det)
            self.central_widget_layout.addWidget(
                current_button,
                row + 1,
                column,
                alignment=Qt.AlignmentFlag.AlignCenter
            )
            if column > 4:
                column = 0
                row += 2

    def init_network_thread(self):
        self.client = ConnectionClient(camera_workers_list=self.camera_workers)
        self.client.add_handlers(AproveUserHandler,
                                 VideoRequestHandler,
                                 StreamHandler)
        self.network_thread = QThread(self)
        self.client.moveToThread(self.network_thread)
        self.client.finished.connect(self.network_thread.quit)
        self.network_thread.started.connect(self.client.run_client)
        self.network_thread.finished.connect(app.exit)
        self.client.connection_status.connect(self.update_connection_status)
        self.client.event_loop_created.connect(self.event_loop_created)
        self.network_thread.start()

    def init_camera_workers(self):
        for camera in CAMERA_LIST:
            current_worker = CameraWorker(camera_name=camera,
                                          camera_source=CAMERA_LIST[camera])
            current_thread = QThread(self)
            self.camera_workers.update({camera: current_worker})
            self.camera_threads.update({camera: current_thread})
            current_worker.moveToThread(current_thread)
            current_worker.finished.connect(current_thread.quit)
            current_thread.started.connect(current_worker.run_camera)
            current_thread.finished.connect(app.exit)
            current_worker.changePixmap.connect(self.setFrame)
            self.enable_detection.connect(current_worker.enable_detection)
            self.disable_detection.connect(current_worker.disable_detection)

    @pyqtSlot()
    def event_loop_created(self):
        self.workers_set_loop()
        self.workers_init()
        self.start_workers()
        self.show()

    def workers_set_loop(self):
        for worker in self.camera_workers:
            self.camera_workers[worker].set_loop(self.client.loop)

    def workers_init(self):
        for worker in self.camera_workers:
            self.camera_workers[worker].init_worker()

    def start_workers(self):
        for camera_name in self.camera_threads:
            self.camera_threads[camera_name].start()

    def enable_det(self):
        self.enable_detection.emit()

    def disable_det(self):
        self.disable_detection.emit()

    @pyqtSlot(QImage, str)
    def setFrame(self, frame, camera_name):
        self.camera_labels[camera_name].setPixmap(QPixmap.fromImage(frame))

    @pyqtSlot(bool)
    def update_connection_status(self, status):
        if status:
            self.status_bar.showMessage('Connection status: OK')
        else:
            self.status_bar.showMessage('Connection status: NO CONNECTION')


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec())
