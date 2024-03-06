import socket
import threading
import time

serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serversocket.bind(('127.0.0.1', 12346))
serversocket.listen(10)

def handle_conn(conn, addr):
    while True:
        msg = conn.recv(1024)
        print(msg.decode())
        answer = msg.decode() + ' answer'
        conn.send(answer.encode())
        time.sleep(10)

while True:
    (conn, addr) = serversocket.accept()
    z = threading.Thread(target=handle_conn, args=(conn, addr))
    z.start()