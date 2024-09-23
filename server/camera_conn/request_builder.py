import json
import time


class ServerRequest:

    writer = None
    reader = None

    def add(self, **kwargs):
        self.client_id = 'main'  # for testing
        self.__dict__.update(kwargs)

    def __eq__(self, other):
        SameObject = isinstance(other, self.__class__)
        if SameObject:
            return True
        if self.__dict__ == other.__dict__:
            return True
        return False

    def __str__(self):
        fields = self.__dict__.copy()
        try:
            del fields['writer']
            del fields['reader']
        except KeyError:
            pass
        return str(fields)

    def serialize(self):
        fields = self.__dict__.copy()
        try:
            del fields['writer']
            del fields['reader']
        except KeyError:
            pass
        serialized = json.dumps(fields) + '\n'
        return serialized


class RequestBuilder:

    def __init__(self):
        self.args = {}
        self.byte_line = None
        self.reset()

    def reset(self):
        self._product = ServerRequest()

    def with_args(self, **kwargs):
        self.args.update(kwargs)
        return self

    def with_bytes(self, byte_line):
        if byte_line:
            args = json.loads(byte_line.decode())
            self.args.update(args)
        return self

    def with_time(self, time):
        self.args.update({'created': time})

    def build(self):
        self.with_time(time.time())
        self._product.add(**self.args)
        return self._product
