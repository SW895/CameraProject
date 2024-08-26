import cv2
# import os
# import json
import base64
import struct
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
    # TIMEZONE,
)


class CameraWorker(QObject):

    videostream_frame = asyncio.Queue(maxsize=1)
    changePixmap = pyqtSignal(QImage, str)
    finished = pyqtSignal()
    _detection = {'car_det': False,
                  'cat_det': False,
                  'chiken_det': False,
                  'human_det': False}

    def __init__(self, camera_name, camera_source):
        super().__init__()
        self.camera_name = camera_name
        self.camera_source = camera_source
        self.log = logging.getLogger(self.camera_name)

    def set_loop(self, loop):
        self.loop = loop

    def send_frame_to_stream(self, frame):
        if self.videostream_frame.qsize() == 0:
            encoded_frame = self.encode(frame)
            try:
                self.loop.call_soon_threadsafe(
                    self.videostream_frame.put_nowait,
                    encoded_frame
                )
            except asyncio.QueueFull:
                self.log.debug('Frame queue full')

    def send_frame_to_GUI(self, frame):
        converted_frame = self.convert_to_QImage(frame)
        self.changePixmap.emit(converted_frame, self.camera_name)

    def detect_objects(self):
        log = logging.getLogger(self.camera_name)
        log.info('CAMERA SOURCE %s', self.camera_source)
        cap = cv2.VideoCapture(self.camera_source)
        self.get_model()
        frames_to_save = []
        if not self.model:
            log.debug('Get model')
            while cap.isOpened():
                success, frame = cap.read()
                if success:
                    results = self.model(frame, conf=0.0001)
                    if results[0]:
                        self.update_detection(results)
                        self._obj_detected = True
                        self._counter = 0
                        log.debug('%s', self._detection)
                    elif self._obj_detected:
                        self._counter += 1

                    if self._counter >= self.no_detection_time:
                        log.debug('Reset counter and detection dict')
                        self.reset_detection_and_counter()

                    if self._obj_detected and \
                       (len(frames_to_save) < BUFF_SIZE):
                        frames_to_save.append(frame)
                    elif self._obj_detected:
                        log.debug('Save video')
                        current_time = datetime.now(tz=self.timezone)
                        self.save_video(frames_to_save,
                                        self._detection,
                                        current_time)
                        self.reset_detection_and_counter()
                        frames_to_save = []

                    self.send_frame_to_stream(frame)
                    self.send_frame_to_GUI(frame)

                    cv2.imshow("YOLOv8 Inference", frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
                else:
                    break

            log.debug('Thread ended')
            cap.release()
            cv2.destroyAllWindows()

    def get_model(self):
        self.model = YOLO(MODEL_PATH)

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
        log = logging.getLogger(self.camera_name)
        log.info('CAMERA SOURCE %s', self.camera_source)
        cap = cv2.VideoCapture(self.camera_source)
        while cap.isOpened():
            success, frame = cap.read()
            if success:
                self.send_frame_to_stream(frame)
                self.send_frame_to_GUI(frame)
            else:
                break
        log.debug('Thread ended')
        cap.release()

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
