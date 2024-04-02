import socket
import queue
import os
import struct
import json
import psycopg
import datetime
import logging
import pytz
from psycopg import sql
from camera_utils import (check_thread, 
                    new_thread, 
                    connect_to_db, 
                    recv_package)


logging.basicConfig(level=90,
                    format="%(name)s | %(levelname)s | %(asctime)s | %(message)s",
                    datefmt="%Y-%m-%dT%H:%M:%S",
                    )


class ServerRequest:

    def __init__(self, request_type, 
                 video_name=None, 
                 video_size=None, 
                 username=None, 
                 email=None,
                 request_result=None,
                 db_record=None):
        
        self.request_type = request_type
        self.video_name = video_name
        self.video_size = video_size
        self.username = username
        self.email = email
        self.request_result = request_result
        self.db_record = db_record


class SocketConn:

    def __init__(self, connection, address, request=None):        
        self.connection = connection
        self.adress = address
        self.request = request


class EchoServer():

    def __init__(self, internal_address, internal_port, external_address, external_port):
        self.stream_queue = queue.Queue(maxsize=1)
        self.stream_q_timeout = 5
        self.signal_queue = queue.Queue()
        self.signal_q_timeout = 5
        self.stream_requesters_queue = queue.Queue()
        self.stream_requesters_timeout = 5
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
        return 'List of request types:' + string

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
                    self.external_handlers[request.request_type](self, request, external_conn, addr)
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

            if request.request_type in self.internal_handlers.keys():
                log.info('Start handler %s', request.request_type)                
                if self.DEBUG:
                        self.test_queue.put('Internal Handler called')  
                self.internal_handlers[request.request_type](self, request, internal_conn, addr)
            else:
                log.warning('Wrong request type. Closing connection')
                if self.DEBUG:
                        self.test_queue.put('Wrong request type')
                internal_conn.close()
            
            if self.DEBUG:
                break
    
    @check_thread
    def ehandler_signal(self, request, conn, addr):
        log = logging.getLogger('Signal thread')
        log.info('Signal thread started')

        self.check_connection(log, conn, 'restart')

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
                conn.send(message.encode())
                if self.DEBUG:
                    self.test_queue.put(message)                
            except:
                log.warning('Connection lost. Shutting down thread')
                break

    def ehandler_stream_source(self, request, conn, addr):
        log = logging.getLogger('Stream source handler')
        log.info('Put stream source connection to stream queue')
        self.stream_queue.put(SocketConn(conn,addr))

    @new_thread
    def ehandler_new_record(self, request, conn, addr):
        log = logging.getLogger('New records')
        result = b""
        data = b""

        self.save_record()
        log.info('Receiving new records')
        while True:                
            data = conn.recv(self.buff_size)
            result += data
            if data == b"" or self.DEBUG:
                break                

        log.info('New records received')
        conn.close()
        records = result.decode().split('\n')
        for record in records:
            if record != "":
                self.save_db_records_queue.put_nowait(json.loads(record))

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
                log.critical('%s, %s', record['date_created'], type(record['date_created']))
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
    
    @new_thread
    def ehandler_video_response(self, request, conn, addr):        
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
                data = conn.recv(655360)
                video_data += data
                if data == b"" or self.DEBUG:
                    break            

            if len(video_data) != request.video_size:
                self.video_response_queue.put(ServerRequest(request_type='video_reponse',
                                                            request_result='failure',
                                                            video_name=request.video_name))
                log.warning('Failed to receive video file')
            else: 
                if self.DEBUG:  
                    video_name_save = os.path.join('/home/moreau/CameraProject/server/djbackend/mediafiles/' 
                                               + request.video_name + '.mp4')    
                else:
                    video_name_save = os.path.join('/home/app/web/mediafiles/' 
                                               + request.video_name + '.mp4')
                log.info('Saving file')
                with open(video_name_save, "wb") as video:
                    video.write(video_data)
                self.video_response_queue.put(ServerRequest(request_type='video_reponse',
                                                            request_result='success',
                                                            video_name=request.video_name))
                log.info('File received')
    
    @new_thread
    def ehandler_user_aprove_response(self, request, conn, addr):
        log = logging.getLogger('User aprove')
        conn.close()
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

    def ihandler_aprove_user_request(self, request, conn, addr):
        conn.close()
        self.signal_queue.put(request)

    def ihandler_stream_request(self, request, conn, addr):
        self.stream_requesters_queue.put(SocketConn(conn,addr))
        self.restream_video()

    def ihandler_video_request(self, request, conn, addr):
        self.video_requesters_queue.put(SocketConn(conn, addr, request=request))
        self.video_manager()

    @check_thread
    def restream_video(self):
        log = logging.getLogger('Videostream')
        log.info('Thread started')
        self.signal_queue.put(ServerRequest(request_type='stream'))
        try:
            stream_conn = self.stream_queue.get(timeout=self.stream_q_timeout)
        except:
            self.signal_queue.put(ServerRequest(request_type='restart stream'))
            log.error('Failed to get stream connection')
            stream_conn = SocketConn(None, None)
        else:
            log.info('Got stream connection')

        requester_list = []    
        payload_size = struct.calcsize("Q")
        data = b""
    
        while stream_conn.connection:
            if self.stream_requesters_queue.qsize() > 0:
                while not(self.stream_requesters_queue.empty()):
                    requester_list.append(self.stream_requesters_queue.get())
        
            stream_conn, frame_data, data, connection_failure = recv_package(
                                                                stream_conn,
                                                                data, 
                                                                payload_size,
                                                                )

            if connection_failure:
                self.signal_queue.put(ServerRequest(request_type='restart stream'))
                log.error('Stream failure')
                break

            if requester_list:
                for requester in requester_list:
                    try:                
                        requester.connection.send(frame_data)
                    except:
                        requester.connection.close()
                        requester_list.remove(requester) 
            else:
                self.signal_queue.put(ServerRequest(request_type='stop'))
                break
            
            if self.DEBUG:
                log.info('End stream because DEBUG')                
                break
        
        if self.DEBUG:
            self.test_queue.put(ServerRequest(request_type='stop'))
        log.info('Stream thread ended')

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
                conn.close()                
                break
            else:
                if reply == b"":
                    conn.close()
                    break
        log.warning('Connection lost')
        if signal != None:
            self.signal_queue.put(ServerRequest(request_type=signal))
        if self.DEBUG:
            self.test_queue.put('connection failed')


if __name__ == "__main__":
    external_addr = os.environ.get('EXTERNAL_HOST', '127.0.0.1')
    external_port = int(os.environ.get('EXTERNAL_PORT', 10900))
    internal_addr = os.environ.get('INTERNAL_HOST', '127.0.0.1')
    internal_port = int(os.environ.get('INTERNAL_PORT', 20900))
    server = EchoServer(internal_addr, internal_port, external_addr, external_port)
    server.run_server()
