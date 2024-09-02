import cv2
import os
import base64
import struct
import threading
import queue
import logging
import asyncio
from ultralytics import YOLO
from datetime import (
    date,
    datetime
)
from PyQt6.QtCore import (
    QObject,
    pyqtSignal,
    pyqtSlot
)
from PyQt6.QtGui import QImage
from settings import (
    MAX_VIDEO_LENGTH,
    MODEL_PATH,
    CONFIDENCE,
    DEFAULT_DETECTION,
    TIMEZONE,
    SAVE_PATH,
    SAVE_FRAME_TIMEOUT,
    NO_DETECTION_LEN
)


class CameraWorker(QObject):

    def __init__(self, camera_name, camera_source):
        super().__init__()
        self.camera_name = camera_name
        self.camera_source = camera_source
        self.log = logging.getLogger(self.camera_name)
        self.videostream_frame = asyncio.Queue(maxsize=1)
        self.changePixmap = pyqtSignal(QImage, str)
        self.finished = pyqtSignal()
        self._lock = threading.Lock()
        self._frame_handler = None
        self._model_exist = False

    @pyqtSlot()
    def enable_detection(self):
        if self._model_exist:
            with self._lock:
                self._frame_handler = DetectingObjects(self.camera_name,
                                                       self.log,
                                                       self._loop,
                                                       self.videostream_frame,
                                                       self.changePixmap,
                                                       self.model)

    @pyqtSlot()
    def disable_detection(self):
        with self._lock:
            self._frame_handler = NoDetecting(self.camera_name,
                                              self.log,
                                              self._loop,
                                              self.videostream_frame,
                                              self.changePixmap)

    def init_worker(self):
        self.get_video_capture()
        try:
            self.get_model()
        except OSError:
            self._model_exist = False
        else:
            self._model_exist = True
        self.set_default_frame_handler()

    def set_default_frame_handler(self):
        with self._lock:
            if DEFAULT_DETECTION and self._model_exist:
                self._frame_handler = DetectingObjects(self.camera_name,
                                                       self.log,
                                                       self._loop,
                                                       self.videostream_frame,
                                                       self.changePixmap,
                                                       self.model)
            else:
                self._frame_handler = NoDetecting(self.camera_name,
                                                  self.log,
                                                  self._loop,
                                                  self.videostream_frame,
                                                  self.changePixmap)

    def get_video_capture(self):
        self.cap = cv2.VideoCapture(self.camera_source)
        self.width = 1
        self.height = 1 # REWORK

    def get_model(self):
        self.model = YOLO(MODEL_PATH)

    def set_loop(self, loop):
        self._loop = loop

    def run_camera(self):
        self.log.info('CAMERA SOURCE %s', self.camera_source)
        while self.cap.isOpened():
            success, frame = self.cap.read()
            if success:
                with self._lock:
                    self._frame_handler.process_frame(frame)
            else:
                break


class FrameProcessing:

    def process_frame(self, frame):
        self.frame = self.process_detections(frame)
        self.send_frame_to_stream(self.frame)
        self.send_frame_to_GUI(self.frame)

    def send_frame_to_stream(self, frame):
        if self.videostream_frame.qsize() == 0:
            encoded_frame = self.encode(frame)
            self._loop.call_soon_threadsafe(
                self.videostream_frame.put_nowait, encoded_frame)

    def send_frame_to_GUI(self, frame):
        converted_frame = self.convert_to_QImage(frame)
        self.gui_signal.emit(converted_frame, self.camera_name)

    def process_detections(self, frame):
        return frame

    def convert_to_QImage(self, frame):
        rgbImage = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, channels = rgbImage.shape
        bytesPerLine = channels * width
        convertToQtFormat = QImage(rgbImage.data,
                                   width,
                                   height,
                                   bytesPerLine,
                                   QImage.Format.Format_RGB888)
        return convertToQtFormat.scaled(640, 480)

    def encode(self, frame):
        ret, jpeg = cv2.imencode('.jpg', frame)
        b64_img = base64.b64encode(jpeg)
        encoded_frame = struct.pack("Q", len(b64_img)) + b64_img
        return encoded_frame


class DetectingObjects(FrameProcessing):

    def __init__(self,
                 camera_name,
                 log,
                 loop,
                 videostream_frame,
                 GUI_signal,
                 model):
        self.camera_name = camera_name
        self.log = log
        self._loop = loop
        self.videostream_frame = videostream_frame
        self.gui_signal = GUI_signal
        self.model = model
        self._detection = {
            'car_det': False,
            'cat_det': False,
            'chiken_det': False,
            'human_det': False,
            'camera_id': self.camera_name
        }
        self._obj_detected = False
        self.frames_to_save = []
        self.video_length = 0
        self.frames_from_last_detection = 0
        self.save_thread = None

    def process_detections(self, frame):
        results = self.model(frame, conf=CONFIDENCE, verbose=False)
        annotated_frame = results[0].plot()
        if results[0]:
            self.frames_from_last_detection = 0
            self.update_detection(results)
            if not self._obj_detected:
                self._obj_detected = True
                width, height = frame.shape[1], frame.shape[0]
                self.save_thread = SaveVideo()
                th = threading.Thread(target=self.save_thread.run,
                                      args=(width, height))
                th.start()
        elif self._obj_detected:
            self.frames_from_last_detection += 1
        if self._obj_detected:
            self.save_thread.frame_queue.put(annotated_frame)
            self.video_length += 1

        if (self.video_length > MAX_VIDEO_LENGTH) or \
           (self.frames_from_last_detection > NO_DETECTION_LEN):
            self.save_thread.update_record(self._detection)
            self.save_thread.end_of_file()
            self.reset_detection_and_counters()
        return annotated_frame

    def update_detection(self, results):
        for r in results:
            for c in r.boxes.cls:
                if not self._detection[self.model.names[int(c)]]:
                    self._detection[self.model.names[int(c)]] = True

    def reset_detection_and_counters(self):
        self._detection = {'car_det': False,
                           'cat_det': False,
                           'chiken_det': False,
                           'human_det': False}
        self.video_length = 0
        self.frames_from_last_detection = 0
        self.save_thread = None
        self._obj_detected = False


class NoDetecting(FrameProcessing):

    def __init__(self,
                 camera_name,
                 log,
                 loop,
                 videostream_frame,
                 GUI_signal):
        self.camera_name = camera_name
        self.log = log
        self._loop = loop
        self.videostream_frame = videostream_frame
        self.gui_signal = GUI_signal


class SaveVideo:

    def __init__(self):
        self.frame_queue = queue.Queue()
        self._end_of_file = threading.Event()
        self._lock = threading.Lock()
        self.log = logging.getLogger('Save video')
        self.record = {}

    def end_of_file(self):
        self._end_of_file.set()

    def not_end_of_file(self):
        return not self._end_of_file.is_set()

    def update_record(self, detection):
        with self._lock:
            self.record.update(detection)
        return self.record

    def run(self, width, height):
        print(self.frame_queue)
        current_time = datetime.now(tz=TIMEZONE)
        self.record.update({'date_created': current_time.isoformat()})
        self.log.debug('Thread started')
        today = date.today()
        today_save_path = SAVE_PATH / (today.strftime("%d_%m_%Y") + '/')
        if not os.path.isdir(today_save_path):
            os.mkdir(today_save_path)

        video_name = os.path.join(
            today_save_path,
            current_time.strftime("%d_%m_%YT%H_%M_%S") + '.mp4'
        )
        self.log.debug('video name: %s', video_name)
        xx = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(video_name,
                              xx,
                              10,
                              (640, 480), isColor=True)
        while self.not_end_of_file():
            try:
                frame = self.frame_queue.get(timeout=SAVE_FRAME_TIMEOUT)
            except queue.Empty:
                break
            else:
                frame = cv2.resize(frame, (640, 480))
                frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
                out.write(frame)
        out.release()
