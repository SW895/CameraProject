import socket
import os
import json

stream_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
stream_socket.settimeout(5.0)
try:
    stream_socket.connect((os.environ.get('INTERNAL_HOST', '127.0.0.1'), 
                                        int(os.environ.get('INTERNAL_PORT', 20900))))
except:
    stream_socket.close()

msg = {'request_type':'stream_request', 'camera_name':'test_camera'}
stream_socket.send(json.dumps(msg).encode())

while True:
    data = stream_socket.recv(65536)
    print(f'DATA RECEIVED {len(data)}')