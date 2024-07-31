import threading
import logging
import json


class SingletonMeta(type):

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


class ErrorAfter(object):
    '''
    Callable that will raise `CallableExhausted`
    exception after `limit` calls

    '''
    def __init__(self, limit, return_value):
        self.limit = limit
        self.calls = 0
        self.return_value = return_value

    def __call__(self, *args):
        self.calls += 1
        if self.calls > self.limit:
            raise CallableExhausted
        return self.return_value


class CallableExhausted(Exception):
    pass


class StatusCode:

    def __init__(status):
        raise NotImplementedError


class ServerRequest:

    def __init__(self, request_type,
                 video_name=None,
                 video_size=None,
                 username=None,
                 email=None,
                 request_result=None,
                 db_record=None,
                 camera_name=None,
                 writer=None,
                 reader=None):

        self.request_type = request_type
        self.video_name = video_name
        self.video_size = video_size
        self.username = username
        self.email = email
        self.request_result = request_result
        self.db_record = db_record
        self.camera_name = camera_name
        self.writer = writer
        self.reader = reader

    def __eq__(self, other):
        SameObject = isinstance(other, self.__class__)
        if SameObject:
            return True
        if (self.request_type == other.request_type) and \
           (self.video_name == other.video_name) and \
           (self.video_size == other.video_size) and \
           (self.username == other.username) and \
           (self.email == other.email) and \
           (self.request_result == other.request_result) and \
           (self.db_record == other.db_record) and \
           (self.camera_name == other.camera_name) and \
           (self.reader == other.reader) and \
           (self.writer == other.writer):
            return True
        return False

    def serialize(self):
        result = self.__dict__.copy()
        del result['writer']
        del result['reader']

        return json.dumps(result)


def check_thread(target_function):

    def inner(*args, **kwargs):

        thread_running = False

        for th in threading.enumerate():
            if th.name == target_function.__name__:
                thread_running = True
                break

        if not thread_running:
            logging.info('Starting thread %s', target_function.__name__)
            thread = threading.Thread(target=target_function,
                                      args=args,
                                      name=target_function.__name__)
            thread.start()
            return thread
        else:
            logging.warning('Thread %s already running',
                            target_function.__name__)

    return inner


def new_thread(target_function):

    def inner(*args, **kwargs):

        thread = threading.Thread(target=target_function,
                                  args=args,
                                  kwargs=kwargs)
        thread.start()
        return thread

    return inner
