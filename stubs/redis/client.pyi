from typing import Optional

class StrictRedis:
    @classmethod
    def from_url(cls, url: str, db: int = None) -> StrictRedis: ...

    def get(self, name: str) -> Optional[bytes]: ...
