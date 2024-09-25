import cv2
import os
import base64
import struct
import threading
import queue
import logging
import asyncio
import torchvision
import numpy
from ultralytics import YOLO
from datetime import (
    date,
    datetime
)
from PyQt6.QtCore import (
    QObject,
    pyqtSignal,
)
from PyQt6.QtGui import QImage
from connection_client import NewRecordHandler
from settings import (
    MAX_VIDEO_LENGTH,
    MODEL_PATH,
    CONFIDENCE,
    DEFAULT_DETECTION,
    TIMEZONE,
    SAVE_PATH,
    SAVE_FRAME_TIMEOUT,
    NO_DETECTION_LEN,
    FPS,
    QT_VIDEO_WIDTH,
    QT_VIDEO_HEIGHT,
    RECORD_VIDEO_TIMEOUT
)


class CameraWorker(QObject):

    changePixmap = pyqtSignal(QImage, str)
    finished = pyqtSignal()

    def __init__(self, camera_name, camera_source):
        super().__init__()
        self.camera_name = camera_name
        self.camera_source = camera_source
        self.log = logging.getLogger(self.camera_name)
        self.videostream_frame = asyncio.Queue(maxsize=1)
        self._frame_handler = None
        self._model_exist = False
        self._detection_enabled = True
        self.detection_policy_event = threading.Event()
        self.recording_event = threading.Event()

    def enable_detection(self):
        print('SIGNAL ENABLE')
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
        print('SIGNAL DISABLE')
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
        return self.detection_policy_event.is_set()

    def change_detection_policy(self):
        if self._detection_enabled:
            self.disable_detection()
        else:
            self.enable_detection()
        self.detection_policy_event.clear()

    def request_change_detection_policy(self):
        self.detection_policy_event.set()

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
            else:
                break

    def start_recording(self):
        self.recording_event.set()

    def stop_recording(self):
        self.recording_event.clear()


class FrameProcessing:

    def process_frame(self, frame):
        processed_frame = self.process_detections(frame)
        self.send_frame_to_stream(processed_frame)
        self.send_frame_to_GUI(processed_frame)
        self.record_video(processed_frame)

    def send_frame_to_stream(self, frame):
        if self.videostream_frame.qsize() == 0:
            encoded_frame = self.encode(frame)
            self._loop.call_soon_threadsafe(
                self.videostream_frame.put_nowait, encoded_frame
            )

    def send_frame_to_GUI(self, frame):
        converted_frame = self.convert_to_QImage(frame)
        self.gui_signal.emit(converted_frame, self.camera_name)

    def process_detections(self, frame):
        return frame

    def convert_to_QImage(self, frame):
        rgbImage = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, channels = rgbImage.shape
        bytesPerLine = channels * width
        convertToQtFormat = QImage(
            rgbImage.data,
            width,
            height,
            bytesPerLine,
            QImage.Format.Format_RGB888
        )
        return convertToQtFormat.scaled(QT_VIDEO_WIDTH, QT_VIDEO_HEIGHT)

    def encode(self, frame):
        ret, jpeg = cv2.imencode('.jpg', frame)
        b64_img = base64.b64encode(jpeg)
        encoded_frame = struct.pack("Q", len(b64_img)) + b64_img
        return encoded_frame

    def record_video(self, frame):
        pass


class DetectingObjects(FrameProcessing):

    def __init__(self, **kwargs):
        self.camera_name = kwargs['camera_name']
        self.log = kwargs['logger']
        self._loop = kwargs['event_loop']
        self.videostream_frame = kwargs['frame_queue']
        self.gui_signal = kwargs['gui_signal']
        self.model = kwargs['model']
        self.resolution = kwargs['resolution']
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
                self.save_thread = SaveVideo(
                    self.resolution,
                    self.camera_name,
                    self._loop
                )
                th = threading.Thread(target=self.save_thread.run)
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
                           'human_det': False,
                           'camera_id': self.camera_name}
        self.video_length = 0
        self.frames_from_last_detection = 0
        self.save_thread = None
        self._obj_detected = False


class NoDetecting(FrameProcessing):

    def __init__(self, **kwargs):
        self.camera_name = kwargs['camera_name']
        self.log = kwargs['logger']
        self._loop = kwargs['event_loop']
        self.videostream_frame = kwargs['frame_queue']
        self.gui_signal = kwargs['gui_signal']
        self.resolution = kwargs['resolution']


class SaveVideo:

    def __init__(self, resolution, camera_name, event_loop):
        self.resolution = resolution
        self.camera_name = camera_name
        self.loop = event_loop
        self.frame_queue = queue.Queue()
        self._end_of_file = threading.Event()
        self._record_updated = threading.Event()
        self._lock = threading.Lock()
        self.log = logging.getLogger('Save video')
        self.record = {}
        self.record_handler = NewRecordHandler()
        self.save_path = SAVE_PATH / self.camera_name
        if not os.path.isdir(self.save_path):
            os.mkdir(self.save_path)

    def end_of_file(self):
        self._end_of_file.set()

    def not_end_of_file(self):
        return not self._end_of_file.is_set()

    def update_record(self, detection):
        with self._lock:
            self.record.update(detection)
        self._record_updated.set()

    def run(self):
        frames = []
        current_time = datetime.now(tz=TIMEZONE)
        self.record.update({'date_created': current_time.isoformat()})
        self.log.debug('Thread started')
        today = date.today()
        today_save_path = self.save_path / (today.strftime("%d_%m_%Y") + '/')
        if not os.path.isdir(today_save_path):
            os.mkdir(today_save_path)

        video_name = os.path.join(
            today_save_path,
            current_time.strftime("%d_%m_%YT%H_%M_%S") + '.mp4'
        )
        self.log.debug('video name: %s', video_name)
        while self.not_end_of_file():
            try:
                frame = self.frame_queue.get(timeout=SAVE_FRAME_TIMEOUT)
            except queue.Empty:
                break
            else:
                frame = cv2.resize(
                    frame,
                    (self.resolution[0], self.resolution[1])
                )
                frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
                frames.append(frame)
        torchvision.io.write_video(video_name, numpy.array(frames), FPS)
        self._record_updated.wait()
        self.log.debug('Put record to queue')
        self.loop.call_soon_threadsafe(
            self.record_handler.record_queue.put_nowait, self.record)


class RecordVideo:

    def __init__(self, resolution, camera_name):
        self.frame_queue = queue.Queue(maxsize=1)
        self.resolution = resolution
        self.camera_name = camera_name

    def record_video(self):
        video_name = SAVE_PATH / self.camera_name
        out = cv2.VideoWriter(
            video_name,
            cv2.VideoWriter_fourcc(*'mp4v'),
            FPS,
            (self.resolution[0], self.resolution[1]),
            isColor=True
        )
        while True:
            try:
                frame = self.frame_queue.get(timeout=RECORD_VIDEO_TIMEOUT)
            except queue.Empty:
                break
            else:
                frame = cv2.resize(
                    frame,
                    (self.resolution[0], self.resolution[1])
                )
                frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
                out.write(frame)
        out.release()
