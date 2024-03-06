import cv2
import os
import torchvision
import numpy as np
import torch

try:
     os.remove('/home/moreau/CameraProject/video/111.mp4')
     print('remove file')
except:
     print('error')
     pass

def save_video(frames_to_save):
     path_to_save = '/home/moreau/CameraProject/video/'
     video_name = os.path.join(path_to_save,'111.mp4')
     torchvision.io.write_video(video_name,np.array(frames_to_save),10)

cap = cv2.VideoCapture(-1)

frames_to_save = []
counter = 0
while cap.isOpened():

        success, frame = cap.read()        

        if success:        
  
            
            cv2.imshow("YOLOv8 Inference", frame)
            frames_to_save.append(frame)
            if counter > 100:
                 break
            counter += 1
            
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
        else:
            break
cap.release()
cv2.destroyAllWindows()

save_video(frames_to_save)
#========================================