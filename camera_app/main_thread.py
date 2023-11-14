from ultralytics import YOLO
import cv2
from datetime import date, datetime
import os
import socket
import threading
import queue
import time
import configparser

#========================================================================

frames_to_save = []
empty_frame_counter = 0
detection = False

path = os.path.abspath(os.path.dirname(__file__))
model_path = path + '/weights/test_weights.pt'
save_path = path[0:(len(path)-10)]+'video_archive/'

model = YOLO(model_path)
cap = cv2.VideoCapture(-1)

frame_queue = queue.Queue(maxsize=1)
sig_queue = queue.Queue(maxsize=1)

config = configparser.ConfigParser()
config.read('camera.ini')


#========================================================================

def save_video(frames_to_save, width, height):
    today = date.today()
    today_save_path = save_path + today.strftime("%d_%m_%Y") + '/'
    
    if not os.path.isdir(today_save_path):
        os.mkdir(today_save_path)

    current_date = datetime.now()
    video_name = os.path.join(today_save_path,current_date.strftime("%d_%m_%Y_%H_%M_%S") + '.mp4')
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(video_name, fourcc, 10.0, (width, height))

    for frames in frames_to_save:
        out.write(frames)

    #TODO 
    #save to django model

#========================================================================
def connect_to_server(frame_queue):
    
    adress = config['DEFAULT']['SERVER_ADRESS']
    port = int(config['DEFAULT']['SERVER_PORT'])

    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            print(f'Connecting to {adress}:{port}')
            sock.connect((adress,port))
            password = config['DEFAULT']['PASSWORD']
            print('SENDING PASSWORD')

            sock.send(password.encode())
            reply = sock.recv(10240)

            print('recieved:',reply.decode())
            if reply.decode() != 'accepted':
                print('Connection refused')
                continue

        except socket.error as err:
            print(f'Failed to connect: {err}')
            time.sleep(5)
            continue

        else:
            print(f'Successfully connect to {adress}:{port}')
            io_thread = threading.Thread(target=port_handler, args=(sig_queue, sock))
            io_thread.start()

            sig = sig_queue.get()
            while True:
                if sig == 'reconnect':
                    print('break:',sig)
                    break
                elif sig == 'stop':
                    print('wait to start transmission')
                    sig = sig_queue.get()
                    continue
                elif sig == 'start':
                    while True:
                        #print('get frame')
                        frame = frame_queue.get()
                        #print('frame from queue')
                        ret, jpeg = cv2.imencode('.jpg', frame)
                        data_bytes = jpeg.tobytes()
                        try:
                            sock.send(data_bytes)
                        except BrokenPipeError or ConnectionResetError:
                            sig = 'reconnect'
                            break

                        if sig_queue.qsize() > 0:                    
                            print('get signal')
                            sig = sig_queue.get()
                            print('signal received:', sig)
                            break
                        else:
                            #print('no signal')
                            continue

        io_thread.join()
        sock.close()

            
def port_handler(sig_queue, sock):
    while True:
        msg = sock.recv(1024).decode()
        print('signal received:', msg)
        if msg == '':
            print('reconnecting')
            sig_queue.put('reconnect')
            break
        elif msg == 'stop':
            print('stop transmission')
            sig_queue.put('stop')
        elif msg == 'start':
            print('start transmission')
            sig_queue.put('start')


#========================================================================

def detection(frame_queue):
    frames_to_save = []
    empty_frame_counter = 0
    detection = False
    a,frame_size = cap.read()
    height, width, channels = frame_size.shape

    while cap.isOpened():

        success, frame = cap.read()        

        if success:
            
            results = model(frame,conf=0.5)

            if results[0]:
                empty_frame_counter = 0
                detection = True
                annotated_frame = results[0].plot()            
            else:
                if detection:
                    empty_frame_counter += 1
                annotated_frame = frame
            
            #annotated_frame = frame
            if frame_queue.empty():
                #print('add frame to queue')
                frame_queue.put(annotated_frame)
            else:
                #print('queue full')
                pass        
            
            cv2.imshow("YOLOv8 Inference", annotated_frame)

            if detection:
                frames_to_save.append(annotated_frame)

            if empty_frame_counter > 20 and detection == True:
                #save_video_thread = threading.Thread(target=save_video, args=(frames_to_save, width, height))
                #save_video_thread.start()
            
                frames_to_save = []
                detection = False
                #break
            
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
        else:
            break
#========================================================================

thread_detection = threading.Thread(target=detection, args=(frame_queue, ))
thread_socket_connection = threading.Thread(target=connect_to_server, args=(frame_queue, ))

thread_detection.start() 
thread_socket_connection.start()

thread_detection.join()
thread_socket_connection.join()

cap.release()
cv2.destroyAllWindows()

