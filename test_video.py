
from ultralytics import YOLO
from datetime import date, datetime
from itertools import cycle
import cv2, os, socket, threading, queue, time, configparser, struct, torchvision, numpy, json

"""
cap = cv2.VideoCapture('video/111.mp4')
new = []

while cap.isOpened():

        success, frame = cap.read()        

        if success:            
           
            annotated_frame = frame            
            #cv2.imshow("YOLOv8 Inference", annotated_frame)

            ret, jpeg = cv2.imencode('.jpg', frame)
            data_bytes = jpeg.tobytes()
 
            new_jpeg = numpy.frombuffer(data_bytes, dtype=numpy.uint8)
   
            new_frame = cv2.imdecode(new_jpeg, cv2.IMREAD_ANYCOLOR)


            cv2.imshow("YOLOv8 Inference", new_frame)
            new.append(new_frame)
            
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
        else:
            break
    
video_name = 'video/222.mp4'


torchvision.io.write_video(video_name,numpy.array(new),10)

"""