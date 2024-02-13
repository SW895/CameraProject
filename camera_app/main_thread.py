import cv2
import os
import threading
import queue
import configparser
import struct
import torchvision
import numpy
import json
import smtplib
import ssl
from utils import check_thread, start_thread, handshake
from ultralytics import YOLO
from datetime import date, datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


@start_thread
def main_connection():
   
    while True:
        sock = handshake(th_name_sig, adress, port, 1)
        if sock:    
            while True:
                print(f'{th_name_sig}:Waiting for a message')
                reply = sock.recv(1024)

                if reply == b"":
                    print(f'{th_name_sig}:Connection broken. Reconnecting ...')
                    sock.close()
                    break
                else:
                    print('Signal received:', reply.decode())
                    signal = reply.decode().split('#')[0]
                    print(signal)
                    if signal in cases.keys():
                        cases[signal](reply.decode())
                    else:
                        json_handler(reply.decode())


def signal_handler(signal):
    sig.put(signal)


def json_handler(line):
    with open('db.json', 'a') as outfile:
        outfile.write(line + '\n')


@check_thread       
def stream_handler(th_name):

    signal = ''

    while True:

        stream_sock = handshake(th_name, adress, port, 2)
        if stream_sock:

            while True:
                    frame = frame_queue.get()
                    ret, jpeg = cv2.imencode('.jpg', frame)
                    data_bytes = jpeg.tobytes() 
                    message = struct.pack("Q",len(data_bytes)) + data_bytes

                    try:
                        stream_sock.sendall(message)

                    except BrokenPipeError:
                        signal = 'Stop'
                        break

                    except ConnectionResetError:
                        signal = 'Restart'
                        break

                    else:
                        if sig.qsize() > 0:                    
                            signal = sig.get()                        
                            break

            stream_sock.close()            
            
            if signal == 'Stop':            
                break

            elif signal == 'Restart':
                print(f'{th_name}: Restarting stream')
                signal = ''
                continue

        else:
            print(f'{th_name}: Failed to connect')
            break

    print(f'{th_name}: Stream ended')
        
    
@start_thread
def approve_user_handler(userstr):

    print(f'{userstr}: thread started')

    username = userstr.split('#')[1].split('|')[0]
    email = userstr.split('#')[1].split('|')[1]   
    user_list = config['USER_LIST']['USER_LIST'].split(' ')

    if username in user_list:
        sock = handshake('ApplyU' + '#' + username + '|' + 'A', adress, port)        
        send_email(email, username, True)
    else:
        sock = handshake('ApplyU' + '#' + username + '|' + 'D', adress, port)        
        send_email(email, username, False)
    sock.close()


def send_email(receiver_email, username, result):
   
    smtp_server = 'smtp.gmail.com'
    sender_email = config['EMAIL']['EMAIL_USER']
    password = config['EMAIL']['EMAIL_PASSWORD']
    email_port = config['EMAIL']['EMAIL_PORT']

    message = MIMEMultipart('alternative')
    
    message['From'] = sender_email
    message['To'] = receiver_email

    if result:
        message['Subject'] = 'Account approved'
        text = """\
        Hi,Your account has been successfully aproved by admin, now you can login with your username and password.
        """
        html = """\
        <html>
        <body>
            <p>
            Hi,Your account has been successfully aproved by admin, now you can login with your username and password.
            </p>
        </body>
        </html>
        """
    else:
        message['Subject'] = 'Account denied'
        text = """\
        Hi,Your account has been denied by admin
        """
        html = """\
        <html>
        <body>
            <p>
            Hi,Your account has been denied by admin.
            </p>
        </body>
        </html>
        """

    part1 = MIMEText(text, 'plain')
    part2 = MIMEText(html, 'html')

    message.attach(part1)
    message.attach(part2)

    context = ssl.create_default_context()

    with smtplib.SMTP(smtp_server, email_port) as server:
        server.starttls(context=context)
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, message.as_string())


@start_thread
def video_handler(th_name):
    print(f'{th_name}: thread started')
    video_name = th_name.split('#')[1]
    full_video_name = save_path + video_name.split('T')[0] + '/' + video_name + '.mp4'

    with open(full_video_name, "rb") as video:
        video_bytes = video.read()
        sock = handshake('VideoR' + '#' + video_name + '|' + str(len(video_bytes)), adress, port, 5)
        sock.sendall(video_bytes)

    sock.close()
    print(f'{video_name}: Thread ended')


@start_thread
def camera_detection(model):
    cap = cv2.VideoCapture(-1)
    frames_to_save = []
    empty_frame_counter = 0
    detection = False

    while cap.isOpened():

        success, frame = cap.read()        

        if success:
            
            results = model(frame,conf=0.5)
            """
            if results[0]:
                empty_frame_counter = 0
                detection = True
                annotated_frame = results[0].plot()            
            else:
                if detection:
                    empty_frame_counter += 1
                annotated_frame = frame
            """
            annotated_frame = frame
            if frame_queue.empty():                
                frame_queue.put(annotated_frame)      
            
            cv2.imshow("YOLOv8 Inference", annotated_frame)

            if detection:
                frames_to_save.append(annotated_frame)

            """
            if empty_frame_counter > 20 and detection == True:
                save_video()            
                frames_to_save = []
                detection = False
                #break
            """
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
        else:
            break
    
    cap.release()
    cv2.destroyAllWindows()

@start_thread
def save_video(frames_to_save):

    today = date.today()
    today_save_path = save_path + today.strftime("%d_%m_%Y") + '/'
    
    if not os.path.isdir(today_save_path):
        os.mkdir(today_save_path)

    current_date = datetime.now()
    video_name = os.path.join(today_save_path,current_date.strftime("%d_%m_%YT%H_%M_%S") + '.mp4')
    torchvision.io.write_video(video_name,numpy.array(frames_to_save),10)   

    new_item = {}
    new_item['date_created'] = current_date.isoformat()
    new_item['human_det'] = True
    new_item['cat_det'] = False
    new_item['car_det'] = False
    new_item['chiken_det'] = False

    new_record = json.dumps(new_item)   

    sock = handshake(th_name_save, adress, port, 2)

    if sock:
        try:
            sock.send(new_record.encode())
        except BrokenPipeError or ConnectionResetError:
            print(f'{th_name_save}: Failed to sent record to DB')
            sock.close()
            with open('db.json', 'a') as outfile:
                outfile.write(new_record + '\n')
        else:
            print(f'{th_name_save}: Successfully send record to DB')
            sock.close()


config = configparser.ConfigParser()
config.read('camera.ini')

adress = config['DEFAULT']['SERVER_ADRESS']
port = int(config['DEFAULT']['SERVER_PORT'])

frames_to_save = []
empty_frame_counter = 0
detection = False

path = os.path.abspath(os.path.dirname(__file__))
model_path = path + '/weights/test_weights.pt'
save_path = path[0:(len(path)-10)]+'video_archive/'

model = YOLO(model_path)

frame_queue = queue.Queue(maxsize=1)
sig = queue.Queue(maxsize=1)

th_name_sig = 'Signum'
th_name_save = 'SaveDB'

cases = {
    'Stream': stream_handler,
    'Stop': signal_handler,
    'Restart': signal_handler,
    'Video': video_handler,
    'AppUSR': approve_user_handler,
}

main_connection()
camera_detection(model)
