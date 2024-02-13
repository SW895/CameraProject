import threading
import socket
import time
from itertools import cycle


def check_thread(target_function):

    def inner(*args, **kwargs):

        thread_running = False

        for th in threading.enumerate():
            if th.name == args[0]:
                thread_running = True
                break

        if not thread_running :
            print(f'{args[0]}: Starting thread')                
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


def handshake(th_name, adress, port, attempts_num=0):
    
    counter = cycle([1]) if attempts_num == 0 else range(0,attempts_num)

    for i in counter:
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            print(f'{th_name}:Connecting to {adress}:{port}')
            sock.connect((adress,port))

        except socket.error as err:
            print(f'{th_name}:Failed to connect: {err}')
            sock.close()  
            time.sleep(5)          
            continue

        else:
            print(f'{th_name}:Successfully connect to {adress}:{port}')            
            try:
                sock.send(th_name.encode())
            except BrokenPipeError or ConnectionResetError:
                print(f'{th_name}:Connection broken. Reconnecting ...')
                sock.close()
                time.sleep(5)
                continue
            else:

                try:
                    reply = sock.recv(1024)
                except OSError:
                    sock.close()
                    time.sleep(5)
                    continue
                else:

                    if reply.decode() == 'accepted':
                        print(f'{th_name}:Connection established')
                        return sock
                    else:
                        sock.close()
                        time.sleep(5)
                        continue
    
    print(f'{th_name}: Connection failed')
    return None