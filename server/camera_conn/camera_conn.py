import socket
import queue
import threading
import os
import struct
import json
import psycopg
import datetime
from psycopg import sql


class SocketConn:

    def __init__(self, name, connection, addr):
        self.name = name
        self.connection = connection
        self.adress = addr


external_addr = os.environ.get('EXTERNAL_HOST', '127.0.0.1')
external_port_tcp = int(os.environ.get('EXTERNAL_PORT', 10900))
internal_addr = os.environ.get('INTERNAL_HOST', '127.0.0.1')
internal_port_tcp = int(os.environ.get('INTERNAL_PORT', 20900))

external_sock =socket.socket(socket.AF_INET, socket.SOCK_STREAM)
external_sock.bind((external_addr,external_port_tcp))
external_sock.listen(10)
print(f'Listening on {external_addr}:{external_port_tcp}')

internal_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
internal_sock.bind((internal_addr,internal_port_tcp))
internal_sock.listen(10)
print(f'Listening on {internal_addr}:{internal_port_tcp}')

stream_queue = queue.Queue(maxsize=1)
signal_queue = queue.Queue()
stream_requesters_queue = queue.Queue()
video_requesters_queue = queue.Queue()
video_response_queue = queue.Queue()
save_queue = queue.Queue()


def check_thread(target_function):

    def inner(*args, **kwargs):

        thread_running = False

        for th in threading.enumerate():
            if th.name == args[0]:
                thread_running = True
                break

        if not thread_running :
            print(f'{args[0]}: Starting thread')
            if args[0] == 'Stream':
                signal_queue.put('Stream')
            thread = threading.Thread(target=target_function, args=args, name=args[0])
            thread.start()               
        else:
            print(f'{args[0]}: thread already running')

        return None
    return inner


def start_thread(target_function):

    def inner(*args, **kwargs):

        thread = threading.Thread(target=target_function, args=args)
        thread.start()

    return inner

@start_thread
def check_connection(th_name, conn, signal_queue=None, signal=None):
    while True:
        try:
            reply = conn.recv(1024)
        except:
            conn.close()
            print(f'{th_name}: Connection lost')
            break
        else:
            if reply == b"":
                conn.close()
                print(f'{th_name}: Connection lost')
                break
    if signal != None:
        signal_queue.put(signal)


@start_thread
def handle_external_conn(external_sock):

    cases = {'StrmIN', 'Signum', 'SaveDB', 'VideoR', 'ApplyU'}    

    while True:
        (external_conn, addr) = external_sock.accept()
        msg = external_conn.recv(1024)
        print('External message received:', msg.decode())

        if msg.decode()[:6] in cases:
            reply = 'accepted'
            try:
                print('Connection established. Sending reply...')
                external_conn.send(reply.encode())
            except BrokenPipeError or ConnectionResetError:
                print('Failed to send reply.')
                external_conn.close()                
        else:
            external_conn.close()
            continue

        if msg.decode() == 'Signum':
            handle_sig('Signum', external_conn, addr)

        elif msg.decode() == 'StrmIN':            
            stream_queue.put(SocketConn('', external_conn, addr))  

        elif msg.decode() == 'SaveDB':
            handle_json('SaveDB', external_conn, addr)
            
        elif msg.decode()[:6] == 'VideoR':
            handle_video_response(msg.decode().split(' ')[1], external_conn, addr, video_response_queue)

        elif msg.decode()[:6] == 'ApplyU':
            handle_user_aprove(msg.decode())
            external_conn.close()


#====================================================================================
#====================================================================================
@start_thread
def handle_user_aprove(msg):
    username = msg.split('|')[1]
    result = msg.split('|')[2]

    db_conn, cur = connect_to_db()
    if db_conn:
        if result == 'A':
            cur.execute("UPDATE registration_customuser SET is_active=True, admin_checked=True WHERE username=(%s);",(username,))
            print('User succesuffly activated')
        else:
            cur.execute("UPDATE registration_customuser SET admin_checked=True WHERE username=(%s);",(username,))
            print('User denied')
            
        db_conn.commit()
        cur.close()
        db_conn.close()    
    else:
        print('Failure')

def connect_to_db():
    try:
        db_conn = psycopg.connect(dbname='hello_django_prod',
                              user='hello_django',
                              password='hello_django',
                              host='db',
                              port='5432')
    except psycopg.errors:
        print('Failed to connect to DB')
        return None, None
    else:
        print('Successfully connected to DB')
        cur = db_conn.cursor()
        return db_conn, cur

@start_thread            
def handle_internal_conn(internal_sock):

    while True:
        (internal_conn, addr) = internal_sock.accept()

        msg = internal_conn.recv(1024)
        print('Internal message received:', msg.decode())

        if msg.decode() == 'Stream':
            stream_requesters_queue.put(SocketConn('Stream', internal_conn, addr))   
            handle_videostream('Stream', stream_requesters_queue, stream_queue)               

        if msg.decode()[:5] == 'Video':
            video_requesters_queue.put(SocketConn(msg.decode().split(' ')[1], internal_conn, addr))
            handle_video('Video', video_requesters_queue, video_response_queue)

        if msg.decode()[:5] == 'AppUS':
            signal_queue.put(msg.decode())

           
#====================================================================================
#====================================================================================
            
@start_thread   
def handle_json(th_name, conn, addr):

    print(f'{th_name}: thread started')
    result = b""
    data = b""

    save_record('save_record')

    while True:                
        data = conn.recv(65536)
        if data == b"":
            break
        else:
            result += data

    print(f'{th_name}: Data received')
    conn.close()

    result = result.decode()
    records = result.split('|')

    for record in records[:-1]:
        save_queue.put_nowait(json.loads(record))    

#====================================================================================
#====================================================================================
 
@check_thread
def save_record(th_name):

    print(f'{th_name}: thread started')
    db_conn, cur = connect_to_db()
    """
    db_conn = psycopg.connect(dbname='hello_django_prod',
                              user='hello_django',
                              password='hello_django',
                              host='db',
                              port='5432')
    cur = db_conn.cursor()
    """
    print(f'{th_name}: Connected to DB')

    while True:        
        record = save_queue.get()
        columns = record.keys()
        values = [record[column] for column in columns]
        ret = sql.SQL('INSERT INTO main_archivevideo({fields}) VALUES ({values});').format(
                    fields=sql.SQL(',').join([sql.Identifier(column) for column in columns]),
                    values=sql.SQL(',').join(values),
        )
        try:
            cur.execute(ret)
        except psycopg.Error as error:
            signal_queue.put(json.dumps(record))
            print(f'{th_name}: Error occured: {error}')
        else:
            print(f'{th_name}: Record saved')
        finally:
            db_conn.commit()
        if save_queue.qsize() == 0:
            break

    cur.close()
    db_conn.close()

#====================================================================================
#====================================================================================

@check_thread
def handle_video(th_name, conn, addr):
    print(f'{th_name}: thread started')
    video_requesters = {}

    while True:
        if video_requesters_queue.qsize() > 0:
            while not(video_requesters_queue.empty()):
                requester = video_requesters_queue.get()
                if requester.name in video_requesters:
                    video_requesters[requester.name].append(requester)
                else:
                    video_request_time = datetime.datetime.now()
                    video_requesters[requester.name] = [video_request_time, requester]
                    signal_queue.put('Video' + ' ' + requester.name)
        
        if video_response_queue.qsize() > 0:
            while not(video_response_queue.empty()):
                video_response = video_response_queue.get()

                if video_response[:1] == 'S':
                    msg = 'Success'                   
                elif video_response[:1] == 'F':
                    msg = 'Failure'

                for requester in video_requesters[video_response[1:]][1:]:                
                    requester.connection.send(msg.encode())
                    
                del video_requesters[video_response[1:]]

        if not video_requesters:
            break

        for item in video_requesters.keys():
            if  (datetime.datetime.now() - video_requesters[item][0]).seconds > 1060:
                del video_requesters[item]

#====================================================================================
#====================================================================================

@start_thread
def handle_video_response(th_name, conn, addr, video_response_queue):

    print(f'{th_name}: Thread started')
    video_name = th_name.split('|')[0]
    video_length = int(th_name.split('|')[1])
    video_data = b""
    data = b""
   
    while True:
        data = conn.recv(655360)
        if data == b"":
            break
        video_data += data

    if len(video_data) != video_length:
        video_response_queue.put('F' + video_name)
        print(f'{th_name}: Failed to receive file')
    else:        
        video_name_save = os.path.join('/home/app/web/mediafiles/' + video_name + '.mp4')
        print('saving video')
        with open(video_name_save, "wb") as video:
            video.write(video_data)
        video_response_queue.put('S' + video_name)
        print(f'{th_name}: File received')
         

#====================================================================================
#====================================================================================

@check_thread
def handle_videostream(th_name, stream_requesters, stream):    

    print(f'{th_name} thread started')

    try:
        stream_conn = stream.get(True,10)
    except:
        signal_queue.put('Restart stream')
        print(f'{th_name}: Stream init connection failure')
    else:
        print(f'{th_name}: Got stream connection')

        requester_list = []    
        payload_size = struct.calcsize("Q")
        data = b""
    
        while stream_conn.connection:
            if stream_requesters.qsize() > 0:
                while not(stream_requesters.empty()):
                    requester_list.append(stream_requesters.get())
        
            stream_conn, frame_data, data, connection_failure = recv_package(
                                                                th_name,
                                                                stream_conn,
                                                                data, 
                                                                payload_size,
                                                                )

            if connection_failure:            
                signal_queue.put('Restart stream')
                print(f'{th_name}: Stream failure')
                break

            if requester_list:
                for requester in requester_list:
                    try:                
                        requester.connection.send(frame_data)
                    except:
                        requester.connection.close()
                        requester_list.remove(requester) 
            else:
                signal_queue.put('Stop')
                break
    
    print(f'{th_name}: Stream ended')

#====================================================================================
#====================================================================================

def recv_package(th_name, conn, data, payload_size):

    def check_conn(packet):
        if packet == b"":
            return True
        else:
            return False
        
    connection_failure = False

    packet = conn.connection.recv(4096)       
    if check_conn(packet):
        conn.connection.close()
        connection_failure = True
        
    if not connection_failure:
        data += packet   
        packed_msg_size = data[:payload_size]
        data = data[payload_size:]        
        msg_size = struct.unpack("Q",packed_msg_size)[0]

        while len(data) < msg_size:
            packet = conn.connection.recv(65536)
            if check_conn(packet):
                conn.connection.close()
                connection_failure = True
                print(f'{th_name}: Stream failure')
                break            
            data += packet       

        frame_data = data[:msg_size]
        data  = data[msg_size:]

        return conn, frame_data, data, False

    else:
        return None, None, None, True



#====================================================================================
#====================================================================================
            
@check_thread
def handle_sig(th_name, conn, addr):
    print(f'{th_name} thread started')
    check_connection(th_name, conn, signal_queue, 'Restart')

    while True:
        signal = signal_queue.get()        
        print(f'{th_name}: Get signal', signal)   
        if signal == 'Restart':
            break     
        try:
            conn.send(signal.encode())
        except BrokenPipeError or ConnectionResetError:
            break
    print(f'{th_name}: Shut down')

#====================================================================================
#====================================================================================

handle_external_conn(external_sock)
handle_internal_conn(internal_sock)