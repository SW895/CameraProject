import cv2
import os
import threading
import logging
import asyncio
from ultralytics import YOLO
from PyQt6.QtCore import (
    QObject,
    pyqtSignal,
)
from PyQt6.QtGui import QImage
from settings import (
    MODEL_PATH,
    DEFAULT_DETECTION,
    SAVE_PATH,
)
from frame_processing import (
    DetectingObjects,
    NoDetecting
)
from video_recoders import RecordVideo


class CameraWorker(QObject):

    changePixmap = pyqtSignal(QImage, str)
    finished = pyqtSignal()
    x = 1

    def __init__(self, camera_name, camera_source):
        super().__init__()
        self.camera_name = camera_name
        self.camera_source = camera_source
        self.log = logging.getLogger(self.camera_name)
        self.videostream_frame = asyncio.Queue(maxsize=1)
        self._frame_handler = None
        self._model_exist = False
        self._detection_enabled = True
        self._detection_policy_event = threading.Event()
        self._recording = threading.Event()
        save_path = SAVE_PATH / self.camera_name
        if not os.path.isdir(save_path):
            os.mkdir(save_path)

    def enable_detection(self):
        if self._model_exist:
            self._detection_enabled = True
            self._frame_handler = DetectingObjects(
                camera_name=self.camera_name,
                logger=self.log,
                event_loop=self._loop,
                frame_queue=self.videostream_frame,
                gui_signal=self.changePixmap,
                resolution=self.resolution,
                model=self.model
            )

    def disable_detection(self):
        self._detection_enabled = False
        self._frame_handler = NoDetecting(
            camera_name=self.camera_name,
            logger=self.log,
            event_loop=self._loop,
            frame_queue=self.videostream_frame,
            gui_signal=self.changePixmap,
            resolution=self.resolution
        )

    def check_detection_policy_event(self):
        return self._detection_policy_event.is_set()

    def change_detection_policy(self):
        if self._detection_enabled:
            self.disable_detection()
        else:
            self.enable_detection()
        self._detection_policy_event.clear()

    def request_change_detection_policy(self):
        self._detection_policy_event.set()

    def init_worker(self):
        self.get_video_capture()
        try:
            self.get_model()
        except OSError:
            self._model_exist = False
        else:
            self._model_exist = True
        self.set_default_frame_handler()
        self.recorder = RecordVideo(
            camera_name=self.camera_name,
            resolution=self.resolution
        )

    def set_default_frame_handler(self):
        if DEFAULT_DETECTION and self._model_exist:
            self.enable_detection()
        else:
            self.disable_detection()

    def get_video_capture(self):
        self.cap = cv2.VideoCapture(self.camera_source)
        self.resolution = (int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                           int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))

    def get_model(self):
        self.model = YOLO(MODEL_PATH)

    def set_loop(self, loop):
        self._loop = loop

    def run_camera(self):
        self.log.info('CAMERA SOURCE %s', self.camera_source)
        while self.cap.isOpened():
            success, frame = self.cap.read()
            if success:
                self._frame_handler.process_frame(frame)
                if self.check_detection_policy_event():
                    self.change_detection_policy()
                if self.recording():
                    self.record_frame(frame)
            else:
                break

    def recording(self):
        return self._recording.is_set()

    def record_frame(self, frame):
        self.recorder.frame_queue.put(frame)

    def start_video_recording(self):
        self._recording.set()
        self.recorder.record_video()

    def stop_video_recording(self):
        self._recording.clear()
        self.recorder.stop_recording()
