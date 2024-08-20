import cv2
import sys
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    # QGridLayout,
    QMainWindow,
    QLabel,
    QVBoxLayout
)
from PyQt6.QtCore import (
    QThread,
    QObject,
    pyqtSignal,
    pyqtSlot,
    # Qt,
)
from PyQt6.QtGui import QPixmap, QImage


class Worker(QObject):
    changePixmap = pyqtSignal(QImage)
    finished = pyqtSignal()

    def process_videostream(self):
        cap = cv2.VideoCapture(-1)
        while cap.isOpened():
            success, frame = cap.read()
            if success:
                rgbImage = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                height, width, channels = rgbImage.shape
                bytesPerLine = channels * width
                convertToQtFormat = QImage(rgbImage.data,
                                           width,
                                           height,
                                           bytesPerLine,
                                           QImage.Format.Format_RGB888)
                p = convertToQtFormat.scaled(640, 480)
                self.changePixmap.emit(p)
        self.finished.emit()


class MainWindow(QMainWindow):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle('ChikenGun 9000')
        self.setGeometry(100, 100, 900, 900)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        lay = QVBoxLayout(self.central_widget)
        self.label = QLabel(self)
        lay.addWidget(self.label)

        self.worker = Worker()
        self.worker_thread = QThread(self)
        self.worker.moveToThread(self.worker_thread)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker_thread.started.connect(self.worker.process_videostream)
        self.worker_thread.finished.connect(app.exit)
        self.worker.changePixmap.connect(self.setFrame)
        print('starting worker ')
        self.worker_thread.start()
        self.show()

    @pyqtSlot(QImage)
    def setFrame(self, frame):
        self.label.setPixmap(QPixmap.fromImage(frame))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec())
