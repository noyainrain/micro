from typing import Union

class TCPServer:
    def listen(self, port: Union[str, int], address: str = ...) -> None: ...
