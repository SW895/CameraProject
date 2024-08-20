from PyQt6.QtCore import QObject


class ConnectionClient(QObject):

    async def signal_connection(self):
        pass

    def add_handler(self):
        pass

    def run_client(self):
        pass
