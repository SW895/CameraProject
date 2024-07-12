import threading
import logging
import socket
import time
import json
from itertools import cycle

def check_thread(target_function):

    def inner(*args, **kwargs):

        thread_running = False

        for th in threading.enumerate():
            if th.name == target_function.__name__:
                thread_running = True
                break

        if not thread_running :
            logging.info('Starting thread %s', target_function.__name__)                
            thread = threading.Thread(target=target_function, args=args, name=target_function.__name__)
            thread.start()
            return thread
        else:
            logging.warning('Thread %s already running', target_function.__name__)  

    return inner

def new_thread(target_function):

    def inner(*args, **kwargs):

        thread = threading.Thread(target=target_function, args=args, kwargs=kwargs)
        thread.start()
        return thread

    return inner

def get_connection(request, attempts_num=0, server_address='127.0.0.1', server_port=10900, buff_size=4096):
        log = logging.getLogger('Get connection')
        counter = cycle([1]) if attempts_num == 0 else range(0,attempts_num)
        log.info('Request type: %s', request.request_type)
        for i in counter:        
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                log.info('Connecting to %s:%s', server_address, server_port)
                sock.connect((server_address, server_port))
            except socket.error as err:
                log.error('Failed to connect: %s', err)
                sock.close()  
                time.sleep(5)          
                continue
            else:  
                log.info('Successfully connected to %s:%s', server_address, server_port)          
                try:
                    sock.send(json.dumps(request.__dict__).encode())
                except BrokenPipeError or ConnectionResetError:
                    log.error('Connection broken. Reconnectiong ...')
                    sock.close()
                    time.sleep(5)
                    continue
                else:
                    try:
                        reply = sock.recv(buff_size)
                    except OSError:
                        sock.close()
                        time.sleep(5)
                        continue
                    else:
                        if reply.decode() == 'accepted':
                            log.info('Connection established')
                            return sock
                        else:
                            sock.close()
                            time.sleep(5)
                            continue

        log.error('Connection failed')
        return None