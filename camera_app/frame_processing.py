import cv2
import base64
import struct
from PyQt6.QtGui import QImage
from settings import (
    MAX_VIDEO_LENGTH,
    CONFIDENCE,
    NO_DETECTION_LEN,
    QT_VIDEO_WIDTH,
    QT_VIDEO_HEIGHT,
)
from video_recoders import SaveVideo


class FrameProcessing:

    def __init__(self, **kwargs):
        self.camera_name = kwargs['camera_name']
        self.log = kwargs['logger']
        self._loop = kwargs['event_loop']
        self.videostream_frame = kwargs['frame_queue']
        self.gui_signal = kwargs['gui_signal']
        self.resolution = kwargs['resolution']

    def process_frame(self, frame):
        processed_frame = self.process_detections(frame)
        self.send_frame_to_stream(processed_frame)
        self.send_frame_to_GUI(processed_frame)

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


class DetectingObjects(FrameProcessing):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.model = kwargs['model']
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
                self.save_thread.run()
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

    pass
