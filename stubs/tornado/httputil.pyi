from typing import Dict, List

class HTTPServerRequest:
    headers: Dict[str, str]
    body: bytes
    query_arguments: Dict[str, List[bytes]]
