from .tcpserver import TCPServer

class HTTPServer(TCPServer):
    def __init__(self, *args: object, **kwargs: object) -> None: ...
