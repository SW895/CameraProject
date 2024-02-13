import threading
import os
import psycopg
import struct


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


@start_thread
def check_connection(th_name, conn, signal_queue=None, signal=None):
    while True:
        try:
            reply = conn.recv(1024)
        except:
            conn.close()
            print(f'{th_name}: Connection lost')
            break
        else:
            if reply == b"":
                conn.close()
                print(f'{th_name}: Connection lost')
                break
    if signal != None and signal_queue:
        signal_queue.put(signal)


def connect_to_db():    
    dbname = os.environ.get('POSTGRES_DB', 'dj_test')
    db_user =  os.environ.get('POSTGRES_USER', 'test_dj')
    db_password =  os.environ.get('POSTGRES_PASSWORD', '123')
    db_host =  os.environ.get('POSTGRES_HOST', 'localhost')
    db_port =  os.environ.get('POSTGRES_PORT', '5432')
    print(dbname, db_user, db_password, db_host)
    try:
        db_conn = psycopg.connect(dbname=dbname,
                                  user=db_user,
                                  password=db_password,
                                  host=db_host,
                                  port=db_port)
    except:
        print('Failed to connect to DB')
        return None, None
    else:
        print('Successfully connected to DB')
        cur = db_conn.cursor()
        return db_conn, cur


def recv_package(th_name, conn, data, payload_size):

    connection_failure = False

    packet = conn.connection.recv(4096)       
    if packet == b"":
        conn.connection.close()
        connection_failure = True
        
    if not connection_failure:
        data += packet   
        packed_msg_size = data[:payload_size]
        data = data[payload_size:]        
        msg_size = struct.unpack("Q",packed_msg_size)[0]

        while len(data) < msg_size:
            packet = conn.connection.recv(65536)
            if packet == b"":
                conn.connection.close()
                connection_failure = True
                print(f'{th_name}: Stream failure')
                break            
            data += packet       

        frame_data = data[:msg_size]
        data  = data[msg_size:]

        return conn, frame_data, data, False

    else:
        return None, None, None, True         