from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QLabel,
    QHBoxLayout,
    QGridLayout,
    QTextEdit,
    QMainWindow
)
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QPixmap
import sys


class MainWindow(QWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setWindowTitle('Image')
        self.setGeometry(0, 0, 1320, 1210)
        label = QLabel()
        pixmap = QPixmap('/home/moreau/CameraProject/camera_app/test.jpg')
        label.setPixmap(pixmap)

        button = QPushButton('AAA')
        button.setCheckable(True)
        button.clicked.connect(self.button_clicked)
        button.setFixedSize(QSize(100,30))

        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(button)
        self.setLayout(layout)
        
        self.show()
    # sender_object.signal_name.connect(receiver_object.slot_name)
    def button_clicked(self, checked):
        print('clicked', checked)


class MainWindow2(QWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setWindowTitle('Alalala')
        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.addStretch()
        titles = ['Yes', 'No', 'Cancel']
        buttons = [QPushButton(title) for title in titles]
        for button in buttons:
            layout.addWidget(button)
        layout.setSpacing(50)
        layout.setContentsMargins(50, 50, 50, 50)
        layout.addStretch()
        
        self.show()


class MainWindow3(QWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setWindowTitle('Login')

        layout = QGridLayout()
        self.setLayout(layout)

        layout.addWidget(QLabel('Username'), 0, 0)
        layout.addWidget(QLineEdit(), 0, 1)
        layout.addWidget(QLabel('Password'), 1, 0)
        layout.addWidget(QLineEdit(echoMode=QLineEdit.EchoMode.Password), 1, 1)
        layout.addWidget(QPushButton('Log in'), 2, 0, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(QPushButton('Close'), 2, 1, alignment=Qt.AlignmentFlag.AlignRight)

        self.show()


class MainWindow4(QMainWindow):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle('Menu')
        self.setGeometry(100, 100, 500, 300)
        self.text_edit = QTextEdit(self)
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu('&File')
        edit_menu = menu_bar.addMenu('&Edit')
        file_menu.addAction('New', lambda: self.text_edit.clear())
        file_menu.addAction('Open', lambda: print('Open'))
        file_menu.addAction('Exit', self.destroy)
        self.setCentralWidget(self.text_edit)
        self.show()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow4()
    sys.exit(app.exec())
