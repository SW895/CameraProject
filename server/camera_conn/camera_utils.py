import threading
import os
import psycopg
import struct
import logging


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
        else:
            logging.warning('Thread %s already running', target_function.__name__)  

        return None
    return inner

def new_thread(target_function):

    def inner(*args, **kwargs):

        thread = threading.Thread(target=target_function, args=args)
        thread.start()

    return inner

def connect_to_db(DEBUG):    
    if DEBUG:
        dbname = 'test_dj_test'
    else:
        dbname = os.environ.get('POSTGRES_DB', 'dj_test')
    db_user =  os.environ.get('POSTGRES_USER', 'test_dj')
    db_password =  os.environ.get('POSTGRES_PASSWORD', '123')
    db_host =  os.environ.get('POSTGRES_HOST', 'localhost')
    db_port =  os.environ.get('POSTGRES_PORT', '5432')

    try:
        db_conn = psycopg.connect(dbname=dbname,
                                  user=db_user,
                                  password=db_password,
                                  host=db_host,
                                  port=db_port)
    except:
        return None, None
    else:
        cur = db_conn.cursor()
        return db_conn, cur