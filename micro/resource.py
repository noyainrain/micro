# TODO

from typing import Dict, List, Tuple, Callable, Optional, cast

from .util import str_or_none

from tornado.httpclient import AsyncHTTPClient, HTTPClientError

IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/svg+xml', 'image/gif']
WEBPAGE_TYPES = ['text/html', 'application/xhtml+xml']

class Resource:
    """TODO Web resource representation with useful meta data."""

    def __init__(self, url: str, content_type: str, *, description: str = None,
                 image: Image = None) -> None:
        if str_or_none(url) is None:
            raise ValueError('blank_url')
        if str_or_none(content_type) is None:
            raise ValueError('blank_content_type')
        self.url = url
        self.content_type = content_type
        self.description = str_or_none(description) if description else None
        self.image = image

    def json(self) -> Dict[str, object]:
        return {
            '__type__': type(self).__name__,
            'url': self.url,
            'content_type': self.content_type,
            'description': self.description,
            'image': self.image.json() if self.image else None
        }

class Image(Resource):
    """TODO.

    image is always none because the image itself is its image representation ;)
    """

    def __init__(self, url: str, content_type: str, *, description: str = None) -> None:
        super().__init__(url, content_type, description=description)

# TODO better name
class Discovery:
    """TODO."""

    def __init__(self) -> None:
        self.handlers = [handle_image] # type: List[Callable[[str, str, bytes], Optional[Resource]]]
        self.cache = {} # type: Dict[str, Resource]

    async def discover(self, url: str) -> Resource:
        """TODO."""
        if url in self.cache:
            return self.cache[url]

        try:
            # TODO max=5 * 1024 * 1024 (default is 100mb, maybe okay?)
            # TODO: handle ValueError (e.g. wrong url scheme)
            # TODO: convert timeout to oserror like for notifications (utility method maybe)
            response = await AsyncHTTPClient().fetch(url)
        except HTTPClientError as e:
            if e.code in (404, 410):
                raise KeyError(url)
            if e.code in (401, 402, 403, 405, 451):
                raise ValueError('{} forbidden [forbidden_resource]'.format(url))
            raise CommunicationError('Server responded with status {}'.format(e.code))
        except OSError as e:
            raise CommunicationError(str(e))
        content_type = response.headers['Content-Type'].split(';', 1)[0]

        resource = None
        for handler in self.handlers:
            resource = handler(response.effective_url, content_type, response.body)
            if resource:
                break
        if not resource:
            resource = Resource(response.effective_url, content_type)

        self.cache[url] = resource
        self.cache[resource.url] = resource
        return resource

def handle_image(url: str, content_type: str, data: bytes) -> Optional[Image]:
    if content_type in IMAGE_TYPES:
        return Image(url, content_type)
    return None

def handle_webpage(url: str, content_type: str, data: bytes) -> Optional[Resource]:
    # TODO implement (see resolve)
    # if data is somehow invalid:
    # raise ValueError('Broken HTML in {} [broken_resource_content]'.format(url))
    if content_type in WEBPAGE_TYPES:
        return Resource(url, content_type)
    return None

# overkill?
#class DiscoveryError(Exception):
#    def __init__(self, msg: str, url: str) -> None:
#        super().__init__(msg, url)
#
#    @property
#    def url(self) -> Optional[str]:
#        return cast(Tuple[str, str], self.args)[1]

# TODO move
class CommunicationError(Exception):
    """See :ref:`CommunicationError`."""
    pass
