import socket
import queue
import os
import struct
import json
import psycopg
import datetime
from psycopg import sql
from utils import (check_connection, 
                    check_thread, 
                    start_thread, 
                    connect_to_db, 
                    recv_package)


class SocketConn:

    def __init__(self, name, connection, addr):
        self.name = name
        self.connection = connection
        self.adress = addr


@start_thread
def handle_external_conn(external_sock, cases):

    while True:
        (external_conn, addr) = external_sock.accept()
        msg = external_conn.recv(1024)
        print('External message received:', msg.decode())

        if msg.decode().split('#')[0] in cases.keys():
            reply = 'accepted'
            try:
                print('Connection established. Sending reply...')
                external_conn.send(reply.encode())
            except BrokenPipeError or ConnectionResetError:
                print('Failed to send reply.')
                external_conn.close()
            else:
                cases[msg.decode().split('#')[0]](msg.decode(), external_conn, addr)                
        else:
            external_conn.close()
            continue


@check_thread
def handle_sig(th_name, conn, addr):
    print(f'{th_name} thread started')
    check_connection(th_name, conn, signal_queue, 'Restart')

    while True:
        signal = signal_queue.get()       
        print(f'{th_name}: Get signal', signal)   
        if signal == 'Restart ':
            break
        try:
            conn.send(signal.encode())
        except:
            break
    print(f'{th_name}: Shut down')


def handle_incoming_stream(th_name, conn, addr):
    stream_queue.put(SocketConn('', conn, addr))


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


@check_thread
def save_record(th_name):

    print(f'{th_name}: thread started')
    db_conn, cur = connect_to_db()

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


@start_thread
def handle_video_response(th_name, conn, addr):
    th_name = th_name.split('#')[1]
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


@start_thread
def handle_user_aprove(msg, conn, addr):
    conn.close()
    username = msg.split('#')[1].split('|')[0]
    result = msg.split('#')[1].split('|')[1]

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


@start_thread            
def handle_internal_conn(internal_sock, cases):

    while True:
        (internal_conn, addr) = internal_sock.accept()

        msg = internal_conn.recv(1024)
        print('Internal message received:', msg.decode())
        if msg.decode().split('#')[0] in cases.keys():
            cases[msg.decode().split('#')[0]](msg.decode(), internal_conn, addr)
        else:
            internal_conn.close()


def handle_aprove_request(msg, conn, addr):
    conn.close()
    signal_queue.put(msg)


def handle_stream_request(msg, conn , addr):
    stream_requesters_queue.put(SocketConn('Stream', conn, addr))
    handle_videostream(msg)


def handle_video_request(msg, conn , addr):
    video_requesters_queue.put(SocketConn(msg.split('#')[1], conn, addr))
    handle_video(msg)


@check_thread
def handle_videostream(th_name):    

    print(f'{th_name} thread started')
    signal_queue.put('Stream')
    try:
        stream_conn = stream_queue.get(True,10)
    except:
        signal_queue.put('Restart stream')
        print(f'{th_name}: Stream init connection failure')
    else:
        print(f'{th_name}: Got stream connection')

        requester_list = []    
        payload_size = struct.calcsize("Q")
        data = b""
    
        while stream_conn.connection:
            if stream_requesters_queue.qsize() > 0:
                while not(stream_requesters_queue.empty()):
                    requester_list.append(stream_requesters_queue.get())
        
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


@check_thread
def handle_video(th_name):
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
                    signal_queue.put('Video' + '#' + requester.name)
        
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


external_cases = {
    'Stream': handle_incoming_stream, 
    'Signum': handle_sig, 
    'SaveDB': handle_json, 
    'VideoR': handle_video_response, 
    'ApplyU': handle_user_aprove,
}

internal_cases = {
    'Stream': handle_stream_request,
    'AppUSR': handle_aprove_request,
    'VidREQ': handle_video_request,
}

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


handle_external_conn(external_sock, external_cases)
handle_internal_conn(internal_sock, internal_cases)