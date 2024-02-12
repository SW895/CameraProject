import socket
import os

def gen():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((os.environ.get('INTERNAL_HOST'),int(os.environ.get('INTERNAL_PORT'))))
    except socket.error:
        sock.close()
        return None          
    else:
        msg = 'Stream'
        try:
            sock.send(msg.encode())
        except BrokenPipeError or ConnectionResetError:
            return None
        else:
            while True:
                frame = sock.recv(250000)
                yield (b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')