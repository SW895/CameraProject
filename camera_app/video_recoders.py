import cv2
import os
import threading
import queue
import logging
import torchvision
import numpy
from datetime import (
    date,
    datetime
)
from PyQt6.QtCore import (
    QObject,
    pyqtSignal,
)
from connection_client import NewRecordHandler
from settings import (
    TIMEZONE,
    SAVE_PATH,
    SAVE_FRAME_TIMEOUT,
    FPS,
    RECORD_VIDEO_TIMEOUT
)
from utils import new_thread


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

    def end_of_file(self):
        self._end_of_file.set()

    def not_end_of_file(self):
        return not self._end_of_file.is_set()

    def update_record(self, detection):
        with self._lock:
            self.record.update(detection)
        self._record_updated.set()

    @new_thread
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


class RecordVideo(QObject):

    thread_ended = pyqtSignal(str)

    def __init__(self, resolution, camera_name):
        super().__init__()
        self.frame_queue = queue.Queue(maxsize=1)
        self.resolution = resolution
        self.camera_name = camera_name
        self._status = threading.Event()

    def record_video(self):
        self._status.set()
        self.start()

    def stop_recording(self):
        self._status.clear()

    def not_end_of_file(self):
        return self._status.is_set()

    @new_thread
    def start(self):
        current_time = datetime.now(tz=TIMEZONE)
        video_name = os.path.join(
            SAVE_PATH / self.camera_name,
            current_time.strftime("%d_%m_%YT%H_%M_%S") + '.mp4'
        )
        out = cv2.VideoWriter(
            video_name,
            cv2.VideoWriter_fourcc(*'mp4v'),
            FPS,
            (self.resolution[0], self.resolution[1]),
            isColor=True
        )
        while self.not_end_of_file():
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
        self.thread_ended.emit(self.camera_name)
