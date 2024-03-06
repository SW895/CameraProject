import socket
import threading
import time

#sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

def client_conn(args):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('127.0.0.1',12346))
    while True:
        msg = str(args) + 'sended msg'
        sock.send(msg.encode())
        reply = sock.recv(1024)
        print(reply.decode())
        time.sleep(10)

def client_conn2(args):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('127.0.0.1',12346))
    while True:
        msg = str(args) + 'sended msg'
        sock.send(msg.encode())
        reply = sock.recv(1024)
        print(reply.decode())
        time.sleep(10)

"""
for i in range(10):
    z = threading.Thread(target=client_conn, args=(sock,i))
    z.start()
"""

x = threading.Thread(target=client_conn, args=(1, ))
x.start()
y = threading.Thread(target=client_conn, args=(2, ))
y.start()
z = threading.Thread(target=client_conn, args=(3, ))
z.start()
v = threading.Thread(target=client_conn, args=(4, ))
v.start()
b = threading.Thread(target=client_conn2, args=(5, ), name='aaa')
b.start()
print(b.is_alive())
"""
while True:
    for th in threading.enumerate():
        if th.name == 'aaa':
            print('True')
            #print(th.name)
        else:
            print('False')
            #print(th.name)
    time.sleep(10)
    """

x.join()
y.join()
z.join()
v.join()
b.join()