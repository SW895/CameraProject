import cv2
import socket
import os
import queue
import configparser
import struct
import torchvision
import numpy
import json
import smtplib
import ssl
import pytz
import logging
import time
import base64
from itertools import cycle
from pathlib import Path
from utils import check_thread, new_thread
from ultralytics import YOLO
from datetime import date, datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


logging.basicConfig(level=logging.DEBUG,
                    format="%(name)s | %(levelname)s | %(asctime)s | %(message)s",
                    datefmt="%Y-%m-%dT%H:%M:%S",
                    )


class ClientRequest:

    def __init__(self, request_type, 
                 video_name=None, 
                 video_size=None, 
                 username=None, 
                 email=None,
                 request_result=None,
                 db_record=None,
                 camera_name=None,
                 connection=None,
                 address=None,
                 lifetime=10):
        
        self.request_type = request_type
        self.video_name = video_name
        self.video_size = video_size
        self.username = username
        self.email = email
        self.request_result = request_result
        self.db_record = db_record
        self.camera_name = str(camera_name)
        self.connection = connection
        self.address = address
        self.lifetime = lifetime

    def __eq__(self ,other):
        SameObject = isinstance(other, self.__class__)
        if SameObject:
            return True
        if (self.request_type == other.request_type) and \
            (self.video_name == other.video_name) and \
            (self.video_size == other.video_size) and \
            (self.username == other.username) and \
            (self.email == other.email) and \
            (self.request_result == other.request_result) and \
            (self.db_record == other.db_record) and \
            (self.camera_name == other.camera_name):
            return True
        else:
            return False


class Camera:

    def __init__(self, camera_source, camera_name):
        self.camera_source = camera_source
        self.camera_name = camera_name
        self.frame_queue = queue.Queue(maxsize=1)


class CameraClient:

    def __init__(self, config):
        self.frame_queue = queue.Queue(maxsize=1)
        self.signal_queue = queue.Queue(maxsize=1)
        self.test_queue = queue.Queue()
        self.server_address = config['DEFAULT']['SERVER_ADRESS']
        self.server_port = int(config['DEFAULT']['SERVER_PORT'])
        self.handlers = self.get_handlers()
        self.buff_size = 4096
        self.user_list = config['USER_LIST']['USER_LIST'].split(' ')
        self.email_user = config['EMAIL']['EMAIL_USER']
        self.email_password = config['EMAIL']['EMAIL_PASSWORD']
        self.email_port = config['EMAIL']['EMAIL_PORT']
        self.email_backend = 'smtp.gmail.com'
        self.base_dir = Path(__file__).resolve().parent.parent
        self.model_path = self.base_dir / 'camera_app/weights/test_weights.pt'
        self.save_path = self.base_dir / 'video_archive/'
        self.DEBUG = False
        self.timezone = pytz.timezone('Europe/Moscow')
        self.SAVE_VIDEO = False
        self.DETECTION = False
        self.model = None
        self.APROVE_ALL = bool(config['USER_LIST']['APROVE_ALL'])
        self.camera_list = self.get_camera_list()

    def __getstate__(self):
        state = self.__dict__.copy()
        del state['frame_queue']
        del state['signal_queue']
        del state['test_queue']
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.frame_queue = queue.Queue(maxsize=1)
        self.signal_queue = queue.Queue(maxsize=1)
        self.test_queue = queue.Queue()

    def get_handlers(self):
        handler_list = [method for method in CameraClient.__dict__ 
                       if callable(getattr(CameraClient, method)) 
                       and method.startswith('handler_')]       
        handlers = {}        
        for item in handler_list:
            handlers[item[8:]] = getattr(CameraClient, item)        
        return handlers

    def get_model(self):
        self.model = YOLO(self.model_path)

    def get_connection(self, request, attempts_num=0):
        log = logging.getLogger('Get connection')
        counter = cycle([1]) if attempts_num == 0 else range(0,attempts_num)
        log.info('Request type: %s', request.request_type)
        for i in counter:        
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                log.info('Connecting to %s:%s', self.server_address, self.server_port)
                sock.connect((self.server_address, self.server_port))
            except socket.error as err:
                log.error('Failed to connect: %s', err)
                sock.close()  
                time.sleep(5)          
                continue
            else:  
                log.info('Successfully connected to %s:%s', self.server_address, self.server_port)          
                try:
                    sock.send(json.dumps(request.__dict__).encode())
                except BrokenPipeError or ConnectionResetError:
                    log.error('Connection broken. Reconnectiong ...')
                    sock.close()
                    time.sleep(5)
                    continue
                else:
                    try:
                        reply = sock.recv(self.buff_size)
                    except OSError:
                        sock.close()
                        time.sleep(5)
                        continue
                    else:
                        if reply.decode() == 'accepted':
                            log.info('Connection established')
                            return sock
                        else:
                            sock.close()
                            time.sleep(5)
                            continue

        log.error('Connection failed')
        return None

    @check_thread
    def signal_connection(self):
        log = logging.getLogger('Signal connection')        
        while True:
            request = ClientRequest(request_type='signal')
            sock = self.get_connection(request, 1)
            if sock:
                while True:
                    log.info('Waiting for a message')
                    reply = sock.recv(self.buff_size)

                    if reply.decode() == "":
                        log.info('Connection broken. Reconnecting ...')
                        sock.close()
                        break
                    else:
                        log.debug('MESSAGE:%s', reply.decode())
                        msg_list = reply.decode().split('|')
                        for msg in msg_list:
                            log.info('Signal list: %s', msg_list)
                            if msg != '':
                                request = json.loads(msg, object_hook=lambda d:ClientRequest(**d))
                                log.info('Signal received: %s', request.request_type)
                            else:
                                continue
                            if request.request_type in self.handlers.keys():
                                log.info('Calling handler: %s', request.request_type)
                                self.handlers[request.request_type](self, request)
                                request = None
                            else:                                
                                if self.DEBUG:
                                    self.test_queue.put('Wrong request')
                        log.info('No new messages')
                        if self.DEBUG:
                                break
                if self.DEBUG:
                    self.test_queue.put('Handler called')
                    break

    def handler_stop(self, request):
        log = logging.getLogger('Handler signal')
        log.info('Put request to the queue')
        self.signal_queue.put(request)

    def handler_corrupted_record(self, request):
        log = logging.getLogger('Handler corrupted records')        
        with open('db.json', 'a') as outfile:
            outfile.write(request.db_record + '\n')
        log.info('Records saved')
        if self.DEBUG:
            self.test_queue.put('Records saved')
    
    def handler_restart_stream(self, request):
        self.handler_stream(request)
    
    def convert_frame(self, frame):
        ret, jpeg = cv2.imencode('.jpg', frame)
        b64_img = base64.b64encode(jpeg)
        message = struct.pack("Q",len(b64_img)) + b64_img
        #ret, jpeg = cv2.imencode('.jpg', frame)
        #data_bytes = jpeg.tobytes() 
        #message = struct.pack("Q",len(data_bytes)) + data_bytes        
        return message

    @new_thread
    def handler_aprove_user_request(self, request):
        log = logging.getLogger('Aprove user request')
        log.info('Thread started')
        username = request.username
        email = request.email   

        if (username in self.user_list) or self.APROVE_ALL:
            request = ClientRequest(request_type='user_aprove_response',
                                    username=username,
                                    request_result='aproved')
            log.info('%s aproved', username)                 
            self.send_email(username, email, True)
        else:
            request = ClientRequest(request_type='user_aprove_response',
                                    username=username,
                                    request_result='denied')
            log.info('%s denied', username)              
            self.send_email(username, email, False)
        sock = self.get_connection(request, 1)
        sock.close()

        if self.DEBUG:
            self.test_queue.put('thread worked')

    def send_email(self, username, email, result):
        message = MIMEMultipart('alternative')
    
        message['From'] = self.email_user
        message['To'] = email

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

        with smtplib.SMTP(self.email_backend, self.email_port) as server:
            server.starttls(context=context)
            server.login(self.email_user, self.email_password)
            server.sendmail(self.email_user, email, message.as_string())

    @new_thread
    def handler_video_request(self, request):
        log = logging.getLogger('Handler video request')
        log.info('thread started')
        full_video_name = self.save_path / (request.video_name.split('T')[0] + '/' + request.video_name + '.mp4')

        if os.path.exists(full_video_name):
            with open(full_video_name, "rb") as video:
                video_bytes = video.read()
                log.debug('video length: %s', len(video_bytes))
                sock = self.get_connection(ClientRequest(request_type='video_response',
                                           video_name=request.video_name,
                                           video_size=str(len(video_bytes))), 1)
                sock.sendall(video_bytes)            
        else:
            sock = self.get_connection(ClientRequest(request_type='video_response',
                                           video_name=request.video_name,
                                           video_size=0), 1)
            log.error('No such video %s', request.video_name)
            self.test_queue.put('no such video')
        sock.close()
        log.info('Thread ended')
        if self.DEBUG:
            self.test_queue.put('video sended')

    @check_thread
    def camera_thread(self):
        cap = cv2.VideoCapture(-1)
        frames_to_save = []
        empty_frame_counter = 0
        detection = False
        self.get_model()

        while cap.isOpened():

            success, frame = cap.read()        

            if success:
                
                if self.DETECTION:
                    results = self.model(frame,conf=0.5)
            
                    if results[0]:
                        empty_frame_counter = 0
                        detection = True
                        annotated_frame = results[0].plot()            
                    else:
                        if detection:
                            empty_frame_counter += 1
                        annotated_frame = frame
                else:
                    annotated_frame = frame
                if self.frame_queue.empty():                
                    self.frame_queue.put(annotated_frame)      
            
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

    @new_thread
    def save_video(self, frames_to_save):
        log = logging.getLogger('Save video')
        log.debug('Thread started')
        today = date.today()
        today_save_path = self.save_path / (today.strftime("%d_%m_%Y") + '/')
        log.debug('Save path: %s', today_save_path)
    
        if not os.path.isdir(today_save_path):
            os.mkdir(today_save_path)

        current_date = datetime.now(tz=self.timezone)
        video_name = os.path.join(today_save_path,current_date.strftime("%d_%m_%YT%H_%M_%S") + '.mp4')
        log.debug('video name: %s', video_name)
        torchvision.io.write_video(video_name,numpy.array(frames_to_save),10)   

        new_item = {}
        new_item['date_created'] = current_date.isoformat()
        new_item['human_det'] = True
        new_item['cat_det'] = False
        new_item['car_det'] = False
        new_item['chiken_det'] = False
        log.debug('new_record: %s', new_item)
        new_record = json.dumps(new_item)   

        sock = self.get_connection(ClientRequest(request_type='new_record',
                                                 db_record=new_item), 1)

        if sock:
            try:
                sock.send(new_record.encode())
            except BrokenPipeError or ConnectionResetError:
                log.error('Failed to sent record to server')
                sock.close()
                with open('db.json', 'a') as outfile:
                    outfile.write(new_record + '\n')
            else:
                log.info('Successfully send record to server')
                sock.close()

    def run_client(self):
        self.init_camera()
        self.signal_connection()
        self.camera_thread(self.camera_list[0])
    
    def init_camera(self):
        request = ClientRequest(request_type='new_record', camera_name='1')
        sock = self.get_connection(request, 1)
        records = ''
        for camera in self.camera_list:
            logging.info('%s',camera.camera_name)
            records += json.dumps({'camera_name':str(camera.camera_name)}) + "\n"
            logging.info(records)
        sock.send(records.encode())
        sock.close()

    def handler_stream(self, request):
        self.videostream(request.camera_name)

    @new_thread
    def videostream(self, camera_name):
        log = logging.getLogger(str(camera_name))
        log.info('Thread started')
        signal = ''

        request = ClientRequest(request_type='stream_source', camera_name=camera_name)
        log.debug('Connecting to server')
        stream_sock = self.get_connection(request, 1)
        camera = None
        for cam in self.camera_list:
            if cam.camera_name == camera_name:
                camera = cam
                break
        if stream_sock:
            log.debug('Connected to server. Stream begin')
            while True:
                try:
                    frame = camera.frame_queue.get(timeout=1)
                except:
                    pass
                else:
                    message = self.convert_frame(frame)
                    #save_frame(message)
                    try:
                        stream_sock.sendall(message)
                    except BrokenPipeError or ConnectionResetError:
                        signal = 'stop'
                        break

            stream_sock.close()                
            if self.DEBUG:
                self.test_queue.put(signal)         

        else:
            log.error('Failed to connect to server')
        if self.DEBUG:
            self.test_queue.put('stream ended')
        log.info('Stream ended')

    def get_camera_list(self):
        # { 'camera_name(serial_number)':'camera_address'}
        # {'123456789':'rtsp://username:password@192.168.1.64/1'}
        #return [Camera(0, '1'), Camera(0, '2'), Camera(0, '3'), Camera(0, '4'), Camera(0,'5'), Camera(0, '6'), Camera(0, '7'), Camera(0,'8'), Camera(0, '9'), Camera(0, '10'), Camera(0, '11'), Camera(0,'12')]
        return [Camera(0, '88'), Camera(0, '99')]
                
    @new_thread
    def camera_thread(self, camera):
        cap = cv2.VideoCapture(camera.camera_source)
        frames_to_save = []
        empty_frame_counter = 0
        detection = False
        self.get_model()
        counter = 0
        while cap.isOpened():

            success, frame = cap.read()

            if success:
                
                if self.DETECTION:
                    results = self.model(frame,conf=0.5)
            
                    if results[0]:
                        empty_frame_counter = 0
                        detection = True
                        annotated_frame = results[0].plot()            
                    else:
                        if detection:
                            empty_frame_counter += 1
                        annotated_frame = frame
                else:
                    annotated_frame = frame               
                for camera in self.camera_list: # FOR DEBUG PURPOSE
                    if camera.frame_queue.qsize() == 0:                
                        camera.frame_queue.put(annotated_frame)
                        message = self.convert_frame(frame)
                        counter = save_frame(message, counter)

            
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


def save_frame(frame, counter):
    if counter == 0:
        with open('z.txt', 'wb') as file:
            file.write(frame)
    return counter

if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read('camera.ini')
    client = CameraClient(config)
    client.run_client()