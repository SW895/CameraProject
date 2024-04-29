import socket
import queue
import os
import struct
import json
import psycopg
import datetime
import logging
import pytz
import time
import threading
from pathlib import Path
from psycopg import sql
from camera_utils import (check_thread, 
                        new_thread, 
                        connect_to_db)


logging.basicConfig(level=logging.DEBUG,
                    format="%(name)s | %(levelname)s | %(asctime)s | %(message)s",
                    datefmt="%Y-%m-%dT%H:%M:%S",
                    )

"""
def check_named_thread(target_function):

    def inner(*args, **kwargs):
        thread_running = False
        camera_name = str(args[1])
        for th in threading.enumerate():
            if th.name == target_function.__name__ + camera_name:
                thread_running = True
                break

        if not thread_running :
            logging.debug('Starting thread %s', target_function.__name__ + camera_name)                
            thread = threading.Thread(target=target_function, args=args, name=target_function.__name__ + camera_name)
            thread.start()               
        else:
            logging.debug('Thread %s already running', target_function.__name__ + camera_name)  

        return None
    return inner
"""
class ServerRequest:

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

class StreamChannel:

    def __init__(self):
        self.consumer_queue = queue.Queue()
        self._mutex = threading.Lock()
        self._thread_working = threading.Event()
        self._thread_working.set()
        self._thread_dead = threading.Event()
        self._thread_dead.set()
        self._source_connected = threading.Event()
        self._consumer_number = 0
        self._has_consumers = threading.Event()
        self.stream_source = None
        self.source_connection_timeout = 1000000
    
    def any_consumers(self):
        return self._has_consumers.is_set()

    def no_consumers(self):
        self._has_consumers.clear()

    def has_consumers(self):
        self._has_consumers.set()

    def thread_dead(self):
        self._thread_dead.set()

    def thread_working(self):
        return self._thread_working.is_set()
    
    def kill_thread(self):
        self._thread_working.clear()
        self._thread_dead.wait()

    def run_thread(self, camera_name):
        self._thread_working.set()
        self._thread_dead.clear()        
        
        self.stream_channel(camera_name)
    
    def wait_source_connection(self):
        return self._source_connected.wait(timeout=self.source_connection_timeout)

    def source_connected(self):
        self._source_connected.set()

    def source_disconnected(self):
        self._source_connected.clear()

    #def stream_source_exist(self):
        #return self._source_connected.is_set()

    def add_consumer(self):
        with self._mutex:
            self._consumer_number += 1
            if self._consumer_number == 1:
                self.has_consumers()
    
    def remove_consumer(self):
        with self._mutex:
            self._consumer_number -= 1
            if self._consumer_number == 0:
                self.no_consumers()

    def consumer_number(self):
        with self._mutex:
            return self._consumer_number

    @new_thread
    def stream_channel(self, camera_name):
        log = logging.getLogger(str(camera_name))
        log.debug('Thread started')
        consumer_list = []

        if self.wait_source_connection():

            while self.thread_working() and (self.consumer_number() > 0):
            
                while self.consumer_queue.qsize() > 0:
                    log.info('Get new consumer')
                    consumer_list.append(self.consumer_queue.get())
            
                if consumer_list:
                    data = self.stream_source.connection.recv(1048576)

                    if data == b"":
                        log.debug('Connection to camera lost')
                        break

                    for consumer in consumer_list:
                        try:
                            consumer.connection.send(data)
                        except:
                            log.debug('Connection to consumer lost')
                            consumer.connection.close()
                            consumer_list.remove(consumer)
                            self.remove_consumer()

        if consumer_list:
            for consumer in consumer_list:
                consumer.connection.close()
        
        self.stream_source.connection.close()
        self.stream_source = None
        self.source_disconnected()
        log.debug('Stream channel closed')
        self.thread_dead()
            
            


class EchoServer:

    def __init__(self, internal_address, internal_port, external_address, external_port):
        self.internal_stream_requests = queue.Queue()
        self.external_stream_responses = queue.Queue()
        self.stream_request_timeout = 5
        self.signal_queue = queue.Queue()
        self.signal_q_timeout = 20
        self.video_requesters_queue = queue.Queue()
        self.video_requesters_timeout = 5
        self.video_response_queue = queue.Queue()
        self.video_response_q_timeout = 5
        self.save_db_records_queue = queue.Queue()
        self.save_db_records_q_timeout = 5
        self.test_queue = queue.Queue()
        self.external_address = external_address
        self.external_port = external_port
        self.internal_address = internal_address
        self.internal_port = internal_port
        self.buff_size = 4096
        self.video_request_timeout = 60
        self.external_handlers = self.get_EHandlers()
        self.internal_handlers = self.get_IHandlers()
        self.DEBUG = False
        self.timezone = pytz.timezone('Europe/Moscow')
        self.base_dir = Path(__file__).resolve().parent.parent
        self.debug_video_save_path = self.base_dir / 'djbackend/mediafiles/'
        self.video_save_path = '/home/app/web/mediafiles/'
        self.camera_records_queue = queue.Queue()
        self.stream_channels = {}


    def __getstate__(self):
        state = self.__dict__.copy()
        del state['stream_queue'],
        del state['signal_queue'],
        del state['stream_requesters_queue'],
        del state['video_requesters_queue'],
        del state['video_response_queue'],
        del state['save_db_records_queue']
        del state['test_queue']
        return state

    def __setstate__(self, state):        
        self.__dict__.update(state)
        self.stream_queue = queue.Queue(maxsize=1)
        self.signal_queue = queue.Queue()
        self.stream_requesters_queue = queue.Queue()
        self.video_requesters_queue = queue.Queue()
        self.video_response_queue = queue.Queue()
        self.save_db_records_queue = queue.Queue()
        self.test_queue = queue.Queue()

    def list_handlers(self):
        string = 'External request types:'
        for item in self.external_handlers.keys():
            string += '\n' + item
        string += '\nInternal request types:'
        for item in self.internal_handlers.keys():
            string += '\n' + item   
        return string

    def get_EHandlers(self):
        external_handler_list = [method for method in EchoServer.__dict__ 
                       if callable(getattr(EchoServer, method)) 
                       and method.startswith('ehandler_')]       
        handlers_ex = {}        
        for item in external_handler_list:
            handlers_ex[item[9:]] = getattr(EchoServer, item)        
        return handlers_ex

    def get_IHandlers(self):
        internal_handler_list = [method for method in EchoServer.__dict__ 
                       if callable(getattr(EchoServer, method)) 
                       and method.startswith('ihandler_')]
        handlers_in = {}
        for item in internal_handler_list:
            handlers_in[item[9:]] = getattr(EchoServer, item)
        return handlers_in
    
    def run_server(self):
        log = logging.getLogger('Run Server')

        self.external_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.external_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.external_sock.bind((self.external_address, self.external_port))
        self.external_sock.listen(10)
        log.info("Listening on %s:%s", self.external_address, self.external_port)

        self.internal_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.internal_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.internal_sock.bind((self.internal_address,self.internal_port))
        self.internal_sock.listen(10)
        log.info("Listening on %s:%s", self.internal_address, self.internal_port)

        self.run_external_server(self.external_sock)
        self.run_internal_server(self.internal_sock)

    @check_thread
    def run_external_server(self, external_sock):
        log = logging.getLogger('External Server')

        while True:
            log.info('Waiting for request...')
            external_conn, addr = external_sock.accept()
            log.info('Request received from: %s', addr)
            msg = external_conn.recv(self.buff_size)
            request = json.loads(msg.decode(), object_hook=lambda d:ServerRequest(**d))
            request.connection = external_conn
            request.address = addr

            if request.request_type in self.external_handlers.keys():
                log.info('Request type accepted. Sending reply')
                reply = 'accepted'
                try:
                    external_conn.send(reply.encode())
                except BrokenPipeError or ConnectionResetError:
                    log.error('Failed to send reply')
                    external_conn.close()
                else:
                    log.info('Start handler %s', request.request_type)
                    self.external_handlers[request.request_type](self, request)
                    if self.DEBUG:
                        self.test_queue.put('External Handler called')  

            else:
                log.warning('Wrong request type. Closing connection')
                if self.DEBUG:
                        self.test_queue.put('Wrong request type')
                external_conn.close()
            
            if self.DEBUG:
                break

    @check_thread
    def run_internal_server(self, internal_sock):
        log = logging.getLogger('Internal Server')
    
        while True:
            internal_conn, addr = internal_sock.accept()
            msg = internal_conn.recv(self.buff_size)
            log.info('Internal request received')
            request = json.loads(msg.decode(), object_hook=lambda d:ServerRequest(**d))
            request.connection = internal_conn
            request.address = addr

            if request.request_type in self.internal_handlers.keys():
                log.info('Start handler %s', request.request_type)
                if self.DEBUG:
                        self.test_queue.put('Internal Handler called')
                self.internal_handlers[request.request_type](self, request)
            else:
                log.warning('Wrong request type. Closing connection')
                if self.DEBUG:
                        self.test_queue.put('Wrong request type')
                internal_conn.close()
            
            if self.DEBUG:
                break
    
    @check_thread
    def ehandler_signal(self, request):
        log = logging.getLogger('Signal thread')
        log.info('Signal thread started')

        self.check_connection(log, request.connection, 'restart')

        while True:
            log.info('Waiting for new signal')
            signal = self.signal_queue.get()
            log.info('Get signal:%s', signal.request_type)   
            if signal.request_type == 'restart':
                log.warning('Shutting down thread due to received signal')
                if self.DEBUG:
                    self.test_queue.put('Signal thread shutdown')
                break
            try:
                log.info('Sending signal')
                message = json.dumps(signal.__dict__ ) + '|'
                request.connection.send(message.encode())
                if self.DEBUG:
                    self.test_queue.put(message)                
            except:
                log.warning('Connection lost. Shutting down thread')
                break
        request.connection.close()

    @new_thread
    def ehandler_new_record(self, request):
        log = logging.getLogger('New records')
        if request.db_record:
            self.save_record()
        elif request.camera_name:
            self.save_or_update_camera()

        result = b""
        data = b""        
        log.info('Receiving new records')
        while True:                
            data = request.connection.recv(self.buff_size)
            result += data
            if data == b"" or self.DEBUG:
                break                

        log.info('New records received')
        request.connection.close()
        records = result.decode().split('\n')
        for record in records:
            if record != "" and request.db_record:
                log.debug('RECORD:%s', record)
                self.save_db_records_queue.put_nowait(json.loads(record))                
            elif record != "" and request.camera_name:
                log.debug('RECORD:%s', record)
                self.camera_records_queue.put(json.loads(record))

    @check_thread
    def save_record(self):
        log = logging.getLogger('Save records to DB')
        log.info('Connection to DB')
        db_conn, cur = connect_to_db(self.DEBUG)

        if db_conn:
            log.info('Successfully connected to db')
            while self.save_db_records_queue.qsize() > 0:
                record = self.save_db_records_queue.get()
                log.info('Got new record')
                columns = record.keys()
                values = [record[column] for column in columns]
                ret = sql.SQL('INSERT INTO main_archivevideo({fields}) VALUES ({values});').format(
                fields=sql.SQL(',').join([sql.Identifier(column) for column in columns]),
                values=sql.SQL(',').join(values),)
                try:
                    cur.execute(ret)
                except psycopg.Error as error:
                    self.signal_queue.put(ServerRequest(request_type='corrupted_record',
                                                        db_record=json.dumps(record)))
                    log.error('Error ocured: %s', error)
                else:                    
                    log.info('Record saved')
                finally:
                    db_conn.commit()

            log.info('No more new records')

            if self.DEBUG:
                self.test_queue.put('Records saved')    
            cur.close()
            db_conn.close()
        
        if self.DEBUG and not db_conn:
            self.test_queue.put('DB connection failed')

    @check_thread
    def save_or_update_camera(self):
        log = logging.getLogger('Save camera to DB')
        log.info('Connection to DB')
        db_conn, cur = connect_to_db(self.DEBUG)
        self.stream_request = {}
        #self.stream_request[stream_request.camera_name] = (queue.Queue(), queue.Queue(maxsize=1))
        if db_conn:
            log.info('Successfully connected to db')
            while self.camera_records_queue.qsize() > 0:
                record = self.camera_records_queue.get()
                log.info('Got new record')
                try:
                    cur.execute("INSERT INTO main_camera(camera_name, is_active) VALUES (%s, True);", (record['camera_name'],))
                    log.info('Camera %s added', record['camera_name'])                    
                except:
                    try:
                        cur.execute("UPDATE main_camera SET is_active=True WHERE camera_name=(%s);",(record['camera_name'],))
                        log.info('Camera %s successfully activated', record['camera_name'])
                    except:
                        log.error('Corrupted camera record')
                self.stream_request[record['camera_name']] = (queue.Queue(), queue.Queue(maxsize=1))
                db_conn.commit()
            cur.close()
            db_conn.close()    

            log.info('No more new records')

            if self.DEBUG:
                self.test_queue.put('Records saved')
        
        if self.DEBUG and not db_conn:
            self.test_queue.put('DB connection failed')
    
    @new_thread
    def ehandler_video_response(self, request):        
        log_name = f'Receive Video:{request.video_name}'
        log = logging.getLogger(log_name)
        log.info('Thread started')
        video_data = b""
        data = b""

        if request.video_size == 0:
            self.video_response_queue.put(ServerRequest(request_type='video_reponse',
                                                        request_result='failure',
                                                        video_name=request.video_name))
            log.error('No such video')
        else:

            while True:
                data = request.connection.recv(655360)
                video_data += data
                if data == b"" or self.DEBUG:
                    break            

            if len(video_data) != request.video_size:
                self.video_response_queue.put(ServerRequest(request_type='video_reponse',
                                                            request_result='failure',
                                                            video_name=request.video_name))
                log.warning('Failed to receive video file')
            else: 
                log.info('%s', self.debug_video_save_path) 
                if self.DEBUG:                    
                    video_name_save = os.path.join(str(self.debug_video_save_path) + '/'
                                               + request.video_name + '.mp4')    
                else:
                    video_name_save = os.path.join(str(self.video_save_path) 
                                               + request.video_name + '.mp4')
                log.info('Saving file')
                with open(video_name_save, "wb") as video:
                    video.write(video_data)
                self.video_response_queue.put(ServerRequest(request_type='video_reponse',
                                                            request_result='success',
                                                            video_name=request.video_name))
                log.info('File received')
    
    @new_thread
    def ehandler_user_aprove_response(self, request):
        log = logging.getLogger('User aprove')
        request.connection.close()
        db_conn, cur = connect_to_db(self.DEBUG)

        if db_conn:
            if request.request_result == 'aproved':
                cur.execute("UPDATE registration_customuser SET is_active=True, admin_checked=True WHERE username=(%s);",(request.username,))
                log.info('User %s successfully activated', request.username)
            else:
                cur.execute("UPDATE registration_customuser SET admin_checked=True WHERE username=(%s);",(request.username,))
                log.info('User %s denied', request.username)
            
            db_conn.commit()
            cur.close()
            db_conn.close()    
        else:
            log.error('Failed to connect to DB')

        if self.DEBUG:
            self.test_queue.put('handler worked')

    def ihandler_aprove_user_request(self, request):
        request.connection.close()
        self.signal_queue.put(request)

    def ihandler_video_request(self, request):
        self.video_requesters_queue.put(request)
        self.video_manager()

    @check_thread
    def video_manager(self):
        log = logging.getLogger('Video Manager')
        log.info('Thread started')
        video_requesters = {}

        while True:
            while self.video_requesters_queue.qsize() > 0:
                requester = self.video_requesters_queue.get()
                log.info('get video requester %s', requester.request.video_name)
                if requester.request.video_name in video_requesters:
                    video_requesters[requester.request.video_name].append(requester)
                else:
                    video_request_time = datetime.datetime.now(tz=self.timezone)
                    video_requesters[requester.request.video_name] = [video_request_time, requester]
                    log.info('put video request to queue')
                    self.signal_queue.put(ServerRequest(request_type='video',
                                                        video_name=requester.request.video_name))

            while self.video_response_queue.qsize() > 0:
                video_response = self.video_response_queue.get()
                log.info('Get video response from queue')

                for requester in video_requesters[video_response.video_name][1:]:            
                    requester.connection.send(video_response.request_result.encode())
                    requester.connection.close()
                    
                del video_requesters[video_response.video_name]

            if not video_requesters:
                log.info('No more video requesters')
                break

            for item in video_requesters.keys():
                if  (datetime.datetime.now(tz=self.timezone) - video_requesters[item][0]).seconds > self.video_request_timeout:
                    log.info('Video requester: %s, timeout', item)
                    self.video_response_queue.put(ServerRequest(request_type='video',
                                                                request_result='failure',
                                                                video_name=item))

        if self.DEBUG:
            self.test_queue.put('work done')

    @new_thread
    def check_connection(self, log, conn, signal=None):
        while True:
            try:
                reply = conn.recv(self.buff_size)
            except:
                break
            else:
                if reply == b"":
                    break
        log.warning('Connection lost')
        if signal != None:
            self.signal_queue.put(ServerRequest(request_type=signal))
        if self.DEBUG:
            self.test_queue.put('connection failed')

    def ehandler_stream_source(self, request):
        self.external_stream_responses.put(request)
    
    def ihandler_stream_request(self, request):
        self.internal_stream_requests.put(request)
        self.videostream_manager()

    @check_thread
    def videostream_manager(self):
        log = logging.getLogger('VideoStream Manager')
        log.debug('Managger started')

        while True:
            while self.internal_stream_requests.qsize() > 0:
                log.info('Get requester')
                stream_requester = self.internal_stream_requests.get()                

                if not stream_requester.camera_name in self.stream_channels:
                    log.debug('CREATE stream channel')
                    self.stream_channels[stream_requester.camera_name] = StreamChannel()
                    
                current_stream_channel = self.stream_channels[stream_requester.camera_name]
                                
                if current_stream_channel.consumer_number() == 0:
                    log.debug('Killing thread %s', stream_requester.camera_name)
                    current_stream_channel.kill_thread()
                    log.debug('Ruuning thread %s', stream_requester.camera_name)
                    current_stream_channel.run_thread(stream_requester.camera_name)
                    log.debug('Send stream request')
                    self.signal_queue.put(ServerRequest(request_type='stream', camera_name=stream_requester.camera_name)) 
            
                current_stream_channel.add_consumer()
                log.debug('Put requester to queue')
                current_stream_channel.consumer_queue.put(stream_requester)

            while self.external_stream_responses.qsize() > 0:
                log.debug('Get response')
                stream_source = self.external_stream_responses.get()
                current_stream_channel = self.stream_channels[stream_source.camera_name]                                   
                current_stream_channel.stream_source = stream_source
                current_stream_channel.source_connected()
                    
  

if __name__ == "__main__":
    external_addr = os.environ.get('EXTERNAL_HOST', '127.0.0.1')
    external_port = int(os.environ.get('EXTERNAL_PORT', 10900))
    internal_addr = os.environ.get('INTERNAL_HOST', '127.0.0.1')
    internal_port = int(os.environ.get('INTERNAL_PORT', 20900))
    server = EchoServer(internal_addr, internal_port, external_addr, external_port)
    server.run_server()
