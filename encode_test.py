import cv2
import time
import struct
import base64
import threading
import asyncio
from PyQt6.QtGui import QImage


def convert_frame(frame):
    ret, jpeg = cv2.imencode('.jpg', frame)
    b64_img = base64.b64encode(jpeg)
    message = struct.pack("Q", len(b64_img)) + b64_img    
    return message


frame_q = asyncio.Queue(maxsize=1)


def main():
    cap = cv2.VideoCapture(0)
    max = 0

    while cap.isOpened():
        success, frame = cap.read()
        if success:
            #if frame_q.empty()
            #loop.call_soon_threadsafe(frame_q.put_nowait, frame)
            #frame_q.put_nowait(frame)
            time_1 = time.time()
            rgbImage = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            height, width, channels = rgbImage.shape
            bytesPerLine = channels * width
            convertToQtFormat = QImage(rgbImage.data,
                                           width,
                                           height,
                                           bytesPerLine,
                                           QImage.Format.Format_RGB888)
            p = convertToQtFormat.scaled(640, 480)
            time_2 = time.time()
            print(time_2 - time_1)
            cv2.imshow("YOLOv8 Inference", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
        else:
            break

    cap.release()
    cv2.destroyAllWindows()


async def frame_rec():
    #while True:
        #frame = await frame_q.get()
        #try:
        #    frame = await asyncio.wait_for(frame_q.get(), timeout=1)
       # except Exception:
       #     pass
        #else:
            
        print('Frame received')

loop = asyncio.new_event_loop()
task = loop.create_task(frame_rec())
th = threading.Thread(target=main)
th.start()
loop.run_until_complete(task)