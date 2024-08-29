import cv2
# import os
# import json
import base64
import struct
import threading
# import numpy
import logging
import asyncio
from ultralytics import YOLO
from datetime import (
    # date,
    datetime
)
from PyQt6.QtCore import (
    QObject,
    pyqtSignal,
)
from PyQt6.QtGui import QImage
from settings import (
    BUFF_SIZE,
    MODEL_PATH,
    CONFIDENCE,
    # TIMEZONE,
)


class CameraWorker(QObject):

    videostream_frame = asyncio.Queue(maxsize=1)
    changePixmap = pyqtSignal(QImage, str)
    finished = pyqtSignal()
    _detected_obj = {'car_det': False,
                     'cat_det': False,
                     'chiken_det': False,
                     'human_det': False}
    _lock = threading.Lock()
    _processing_video = threading.Event()
    _detection = threading.Event()
    _processing_thread_ended = threading.Event()

    def __init__(self, camera_name, camera_source):
        super().__init__()
        self.camera_name = camera_name
        self.camera_source = camera_source
        self.log = logging.getLogger(self.camera_name)

    def processing_video(self):
        return self._processing_video.is_set()

    def stop_video_processing(self):
        self._processing_video.clear()

    def start_video_processing(self):
        self._processing_video.set()

    def get_cap(self):
        self.cap = cv2.VideoCapture(self.camera_source)

    def set_loop(self, loop):
        self._loop = loop

    def send_frame_to_stream(self, frame):
        if self.videostream_frame.qsize() == 0:
            encoded_frame = self.encode(frame)
            self._loop.call_soon_threadsafe(
                self.videostream_frame.put_nowait, encoded_frame)

    def send_frame_to_GUI(self, frame):
        converted_frame = self.convert_to_QImage(frame)
        self.changePixmap.emit(converted_frame, self.camera_name)

    def detect_objects(self):
        self.log.info('CAMERA SOURCE %s', self.camera_source)
        frames_to_save = []
        if not self.model:
            raise OSError
        while self.cap.isOpened() and self.processing_video():
            success, frame = self.cap.read()
            if success:
                results = self.model(frame, conf=CONFIDENCE)
                if results[0]:
                    self.update_detection(results)
                    self._obj_detected = True
                    self._counter = 0
                    self.log.debug('%s', self._detection)
                elif self._obj_detected:
                    self._counter += 1

                if self._counter >= self.no_detection_time:
                    self.log.debug('Reset counter and detection dict')
                    self.reset_detection_and_counter()

                if self._obj_detected and (len(frames_to_save) < BUFF_SIZE):
                    frames_to_save.append(frame)
                elif self._obj_detected:
                    self.log.debug('Save video')
                    current_time = datetime.now(tz=self.timezone)
                    self.save_video(frames_to_save,
                                    self._detection,
                                    current_time)
                    self.reset_detection_and_counter()
                    frames_to_save = []

                self.send_frame_to_stream(frame)
                self.send_frame_to_GUI(frame)
            else:
                break

    def get_model(self):
        try:
            self.model = YOLO(MODEL_PATH)
        except OSError:
            self.log.error('NO WEIGHTS')

    def update_detection(self, results):
        for r in results:
            for c in r.boxes.cls:
                if not self._detection[self.model.names[int(c)]]:
                    self._detection[self.model.names[int(c)]] = True

    def reset_detection_and_counter(self):
        self._detection = {'car_det': False,
                           'cat_det': False,
                           'chiken_det': False,
                           'human_det': False}
        self._counter = 0
        self._obj_detected = False

    def no_detection(self):
        self.log.info('CAMERA SOURCE %s', self.camera_source)
        while self.cap.isOpened() and self.processing_video():
            success, frame = self.cap.read()
            if success:
                self.send_frame_to_stream(frame)
                self.send_frame_to_GUI(frame)
            else:
                break
        self.log.debug('Thread ended')

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

    def run_worker(self):
        # if self.detection:
        #    self.detect_objects()
        # else:
        self.start_video_processing()
        self.no_detection()

    """
    REWORK!!!!!!!

    def save_video(self, frames_to_save, new_item):
        current_time = datetime.now()
        log = logging.getLogger('Save video')
        log.debug('Thread started, video length: %s, detection: %s',
            len(frames_to_save),
            new_item)
        today = date.today()
        today_save_path = self.save_path / (today.strftime("%d_%m_%Y") + '/')
        log.debug('Save path: %s', today_save_path)
        if not os.path.isdir(today_save_path):
            os.mkdir(today_save_path)

        video_name = os.path.join(
            today_save_path,
            current_time.strftime("%d_%m_%YT%H_%M_%S") + '.mp4')
        log.debug('video name: %s', video_name)
        torchvision.io.write_video(video_name, numpy.array(frames_to_save), 10)

        new_item['date_created'] = current_time.isoformat()
        new_item['camera_id'] = self.camera_name
        log.debug('new_record: %s', new_item)
        new_record = json.dumps(new_item)
        sock = get_connection(ClientRequest(request_type='new_record',
                                            db_record='new_item'),
                                attempts_num=1,
                                server_address=self.server_address,
                                server_port=self.server_port)

        if sock:
            try:
                sock.send(new_record.encode())
            except BrokenPipeError or ConnectionResetError:
                log.error('Failed to sent record to server')
                with open((self.base_dir / filename), 'a') as outfile:
                    outfile.write(new_record + '\n')
            else:
                log.info('Successfully send record to server')
            sock.close()
    """
