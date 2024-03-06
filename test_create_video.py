import cv2, torchvision, numpy
names = ['20_01_2024T14_25_34', '12_02_2024T09_23_12', '24_05_2024T23_23_12', '09_09_2024T17_09_01']



cap = cv2.VideoCapture(-1)
new = []
video = []
while cap.isOpened():

        success, frame = cap.read()        

        if success:            
           
            #annotated_frame = frame            
            #cv2.imshow("YOLOv8 Inference", annotated_frame)      


            cv2.imshow("YOLOv8 Inference", frame)
            new.append(frame)
            if len(new) == 100:
                video.append(new)
                new = []
                print('new video')

            if len(video) == 4:
                 break
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
        else:
            break
    
#video_name = 'video/222.mp4'
i = 0
for vid in video:     
    video_name = 'video/' + names[i] + '.mp4'
    torchvision.io.write_video(video_name,numpy.array(vid),10)
    i += 1
      