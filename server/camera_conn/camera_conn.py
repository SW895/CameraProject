import socket
import queue
import threading
import time
import os
sig_queue = queue.Queue()

serversocket_out = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#serversocket_out.bind(('127.0.0.1',12345)
print(os.environ.get('PGG_HOST'))
serversocket_out.bind((os.environ.get('PGG_HOST'),12345))
serversocket_out.listen(5)

serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serversocket.bind(('0.0.0.0',1555))
serversocket.listen(5)

def out_conn(sig_queue, in_sock):
    while True:
        (out_sock,addr) = serversocket_out.accept()
        print('connected to local web server')
 
        msg = out_sock.recv(1024)
        if msg.decode() == 'receive':
            try:
                in_sock.send('start'.encode())
            except BrokenPipeError or ConnectionResetError:
                #sig_queue.put('reconnect')
                break
            while True:
                frame = in_sock.recv(250000)
                #print('data received')
                try:
                    out_sock.send(frame)
                    #print('data sended')
                except BrokenPipeError or ConnectionResetError:
                    msg = 'stop'
                    in_sock.send(msg.encode())
                    print('stop transmision')
                    break
            out_sock.close()
        

while True:
    print('try connection')
    (clientsocket, adress) = serversocket.accept()
            #c1 = client_thread(clientsocket)
    msg = clientsocket.recv(1024)
    if msg.decode() == '123':                
        print('connection established')
        reply = 'accepted'
        clientsocket.send(reply.encode())
                #msg2 = clientsocket.recv(1024)
        time.sleep(2)
                #if msg2.decode == 'ready to sent data':
        out_thread = threading.Thread(target=out_conn, args=(sig_queue, clientsocket))
        out_thread.start()
