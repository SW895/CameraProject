import socket
import os

def gen():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('127.0.0.1',12345))
    #print(os.environ.get('PG_HOST'),os.environ.get('PG_PORT'))
    #s.connect((os.environ.get('PG_HOST'), int(os.environ.get('PG_PORT'))))
    #msg = 'receive'
    #s.send(msg.encode())

    while True:
        frame = s.recv(250000)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')