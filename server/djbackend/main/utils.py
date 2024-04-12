import socket
import os
import json
import threading
import logging
import struct


def gen():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((os.environ.get('INTERNAL_HOST', '127.0.0.1'), int(os.environ.get('INTERNAL_PORT', 20900))))
    except socket.error:
        sock.close()
        return b""
    else:
        msg = {'request_type':'stream_request'}
        try:
            sock.send(json.dumps(msg).encode())
        except BrokenPipeError or ConnectionResetError:
            return b""
        else:
            while True:
                frame = sock.recv(1048576)
                yield (b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

def check_named_thread(target_function):

    def inner(*args, **kwargs):
        thread_running = False
        camera_name = str(args[0])

        for th in threading.enumerate():
            if th.name == target_function.__name__ + camera_name:
                thread_running = True
                break

        if not thread_running :
            logging.debug('Starting thread %s', target_function.__name__ + camera_name)                
            thread = threading.Thread(target=target_function, args=args, name=target_function.__name__)
            thread.start()               
        else:
            logging.debug('Thread %s already running', target_function.__name__ + camera_name)  

        return None
    return inner

def recv_package(connection, data, payload_size):
    connection_failure = False

    packet = connection.recv(4096)
    if packet == b"":
        connection.close()
        connection_failure = True
        
    if not connection_failure:
        data += packet   
        packed_msg_size = data[:payload_size]
        data = data[payload_size:]
        msg_size = struct.unpack("Q",packed_msg_size)[0]

        while len(data) < msg_size:
            packet = connection.recv(1048576)
            if packet == b"":
                connection.close()
                connection_failure = True
                print(f'Stream failure')
                break
            data += packet

        frame_data = data[:msg_size]
        data  = data[msg_size:]

        return connection, frame_data, data, False

    else:
        return None, None, None, True         