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
import threading
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
                 address=None,):
        
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

    def __eq__(self, other):
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
            (self.camera_name == other.camera_name) and \
            (self.connection == other.connection) and \
            (self.address == other.address):
            return True
        return False


class CameraSource:

    def __init__(self, camera_source, camera_name, client):
        self.camera_source = camera_source
        self.camera_name = camera_name
        self.model = None
        self.base_dir = Path(__file__).resolve().parent.parent
        self.model_path = self.base_dir / 'camera_app/weights/test_weights.pt'
        path = 'video_archive/' + self.camera_name + '/'
        self.save_path = self.base_dir / path
        self.frame_queue = queue.Queue(maxsize=1)
        self.buff_size = 100
        self._thread_working = threading.Event()
        self._thread_working.set()
        self._thread_dead = threading.Event()
        self._thread_dead.set()
        self.client = client
        self._detection = {'car_det':False, 'cat_det':False, 'chiken_det':False, 'human_det':False}
        self._counter = 0
        self.no_detection_time = 100
        self._obj_detected = False
        self.timezone = pytz.timezone('Europe/Moscow')

        if not os.path.isdir(self.save_path):
            os.mkdir(self.save_path)
    
    def __getstate__(self):
        state = self.__dict__.copy()
        del state['frame_queue']
        del state['save_queue']
        del state['_thread_working']
        del state['_thread_dead']
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.frame_queue = queue.Queue(maxsize=1)
        self._thread_working = threading.Event()
        self._thread_dead = threading.Event()
    
    def thread_dead(self):
        self._thread_dead.set()

    def thread_working(self):
        return self._thread_working.is_set()
    
    def kill_thread(self):
        self._thread_working.clear()
        self._thread_dead.wait()

    def run_thread(self):
        self._thread_working.set()
        self._thread_dead.clear()
        self.videostream()

    def get_model(self):
        self.model = YOLO(self.model_path)
    
    def update_detection(self, results):
        for r in results:
            for c in r.boxes.cls:
                if not self._detection[self.model.names[int(c)]]:
                    self._detection[self.model.names[int(c)]] = True

    def reset_detection_and_counter(self):
        self._detection = {'car_det':False, 'cat_det':False, 'chiken_det':False, 'human_det':False}
        self._counter = 0
        self._obj_detected = False

    @new_thread
    def camera_thread(self):
        logging.info('CAMERA SOURCE %s', self.camera_source)
        log = logging.getLogger(self.camera_name)
        cap = cv2.VideoCapture(self.camera_source)
        self.get_model()
        frames_to_save = []
        if self.model:
            log.debug('Get model')
            while cap.isOpened():
                success, frame = cap.read()

                if success:
                    results = self.model(frame, conf=0.0001)
                    if results[0]:
                        self.update_detection(results)
                        self._obj_detected = True
                        self._counter = 0
                        log.debug('%s', self._detection)
                    elif self._obj_detected:
                        self._counter += 1
                
                    if self._counter >= self.no_detection_time:
                        log.debug('Reset counter and detection dict')
                        self.reset_detection_and_counter()
                                    
                    if self._obj_detected and (len(frames_to_save) < self.buff_size):
                        frames_to_save.append(frame)
                    elif self._obj_detected:
                        log.debug('Save video')
                        self.save_video(frames_to_save, self._detection)
                        self.reset_detection_and_counter()
                        frames_to_save = []

                    if self.frame_queue.qsize() == 0:
                        self.frame_queue.put(frame)
                
                    cv2.imshow("YOLOv8 Inference", frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
                else:
                    break

            cap.release()
            cv2.destroyAllWindows()
    
    @new_thread
    def videostream(self):
        log = logging.getLogger(self.camera_name)
        log.info('Thread started')
        request = ClientRequest(request_type='stream_source', camera_name=self.camera_name)
        log.debug('Connecting to server')
        stream_sock = self.client.get_connection(request, 1)

        if stream_sock:
            log.debug('Connected to server. Stream begin')
            while self.thread_working():
                try:
                    frame = self.frame_queue.get(timeout=1)
                except:
                    continue
                else:
                    message = self.convert_frame(frame)
                    try:
                        stream_sock.sendall(message)
                    except:
                        log.error('Connection to server broken')
                        break
            stream_sock.close()

        self.thread_dead()
        log.info('Stream ended')
    
    def convert_frame(self, frame):
        ret, jpeg = cv2.imencode('.jpg', frame)
        b64_img = base64.b64encode(jpeg)
        message = struct.pack("Q",len(b64_img)) + b64_img    
        return message

    @new_thread
    def save_video(self, frames_to_save, new_item):
        log = logging.getLogger('Save video')
        log.debug('Thread started, video length: %s, detection: %s', len(frames_to_save), new_item)
        today = date.today()
        today_save_path = self.save_path / (today.strftime("%d_%m_%Y") + '/')
        log.debug('Save path: %s', today_save_path)    
        if not os.path.isdir(today_save_path):
            os.mkdir(today_save_path)

        current_date = datetime.now(tz=self.timezone)
        video_name = os.path.join(today_save_path,current_date.strftime("%d_%m_%YT%H_%M_%S") + '.mp4')
        log.debug('video name: %s', video_name)
        torchvision.io.write_video(video_name,numpy.array(frames_to_save),10)   

        new_item['date_created'] = current_date.isoformat()
        log.debug('new_record: %s', new_item)
        new_record = json.dumps(new_item)
        sock = client.get_connection(ClientRequest(request_type='new_record',
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


class CameraClient:

    def __init__(self, config):
        self.DEBUG = False
        self.stream_request_queue = queue.Queue()
        self.server_address = config['DEFAULT']['SERVER_ADRESS']
        self.server_port = int(config['DEFAULT']['SERVER_PORT'])
        self.handlers = self.get_handlers()
        self.buff_size = 4096
        self.base_dir = Path(__file__).resolve().parent.parent
        self.save_path = self.base_dir / 'video_archive/'
        self.user_list = config['USER_LIST']['USER_LIST'].split(' ')
        self.email_user = config['EMAIL']['EMAIL_USER']
        self.email_password = config['EMAIL']['EMAIL_PASSWORD']
        self.email_port = config['EMAIL']['EMAIL_PORT']
        self.email_backend = 'smtp.gmail.com'        
        self.APROVE_ALL = bool(config['USER_LIST']['APROVE_ALL'])
        self.camera_sources = {}
        self._videostream_manager = threading.Event()

    def __getstate__(self):
        state = self.__dict__.copy()
        del state['stream_request_queue']
        del state['_videostream_manager']
        return state

    def __setstate__(self, state):
        self.stream_request_queue = queue.Queue()
        self._videostream_manager = threading.Event()
        self.__dict__.update(state)

    def run_videostream_manager(self):
        self._videostream_manager.clear()
    
    def kill_videostream_manager(self):
        self._videostream_manager.set()

    def videostream_manager_running(self):
        return not self._videostream_manager.is_set()
    
    def get_handlers(self):
        handler_list = [method for method in CameraClient.__dict__ 
                       if callable(getattr(CameraClient, method)) 
                       and method.startswith('handler_')]       
        handlers = {}        
        for item in handler_list:
            handlers[item[8:]] = getattr(CameraClient, item)        
        return handlers

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
                        log.info('No new messages')
                        if self.DEBUG:
                                break
                if self.DEBUG:
                    break

    def handler_corrupted_record(self, request):
        log = logging.getLogger('Handler corrupted records')        
        with open('db.json', 'a') as outfile:
            outfile.write(request.db_record + '\n')
        log.info('Records saved')

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
        sock.close()
        log.info('Thread ended')

    def run_client(self):
        self.get_camera_sources()
        self.init_camera()
        self.signal_connection()
    
    def init_camera(self):
        request = ClientRequest(request_type='new_record', camera_name='1')
        sock = self.get_connection(request, 1)
        records = ''
        for camera in self.camera_sources.keys():
            logging.info('%s',camera)
            records += json.dumps({'camera_name':str(camera)}) + "\n"
            self.camera_sources[camera].camera_thread()

        if sock:
            try:
                sock.send(records.encode())
            except:
                pass
            sock.close()

    def handler_stream(self, request):
        self.stream_request_queue.put(request)
        self.videostream_manager()

    def get_camera_sources(self):
        # { 'camera_name(serial_number)':'camera_address'}
        # {'123456789':'rtsp://username:password@192.168.1.64/1'}
        #TODO REFACTORING
        #camera_list = [(0, 'aaa'),(0, 'bbb'),(0, 'ccc'),(0, 'ddd'),(0, 'eee'),(0, 'fff'),(0, 'ggg'),(0, 'hhh'),(0, 'iii'),(0, 'kkk'),(0, 'lll'),(0, 'mmm')]
        camera_list = [(0,'222')]
        for camera in camera_list:
            self.camera_sources[camera[1]] = CameraSource(camera[0], camera[1], self)

    @check_thread
    def videostream_manager(self):
        self.replicator()
        while self.videostream_manager_running():
            requester = self.stream_request_queue.get()
            current_stream_source = self.camera_sources[requester.camera_name]
            logging.info('KILLING THREAD')
            current_stream_source.kill_thread()
            logging.info('STARTING THREAD')
            current_stream_source.run_thread()
    
    #@check_thread
    #def replicator(self):
    #    while True:
    #        frame = test1.frame_queue.get()
    #        for camera in self.camera_sources.keys():
    #            if self.camera_sources[camera].frame_queue.qsize() == 0:
    #                self.camera_sources[camera].frame_queue.put(frame)


if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read('camera.ini')
    client = CameraClient(config)
    client.run_client()
