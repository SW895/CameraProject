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
