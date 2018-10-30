# TODO

import errno
import os
from typing import Dict, List, Tuple, Callable, Optional, cast

from .error import CommunicationError, Exception
from .util import str_or_none

from tornado.httpclient import AsyncHTTPClient, HTTPClientError, HTTPResponse
from tornado.simple_httpclient import HTTPStreamClosedError, HTTPTimeoutError

IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/svg+xml', 'image/gif']
WEBPAGE_TYPES = ['text/html', 'application/xhtml+xml']

Handle = Callable[[str, str, bytes], Optional['Resource']]

class Resource:
    """TODO Web resource representation with useful meta data."""

    def __init__(self, url: str, content_type: str, *, description: str = None,
                 image: 'Image' = None) -> None:
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

class Analyzer:
    """TODO.

    .. attribute:: handlers

       TODO. Defaults to all builtin handlers.
    """

    def __init__(self, *, handlers: List[Handle] = None) -> None:
        self.handlers = ([handle_image, handle_webpage] if handlers is None
                         else list(handlers)) # type: List[Handle]
        self._cache = {} # type: Dict[str, Resource]

    async def analyze(self, url: str) -> Resource:
        """Analyze the resource at *url*.

        CommunicationError, AnalysisError.
        """
        if url in self._cache:
            return self._cache[url]

        resource = None
        response = await self.fetch(url)
        content_type = response.headers['Content-Type'].split(';', 1)[0]
        for handle in self.handlers:
            resource = handle(response.effective_url, content_type, response.body)
            if resource:
                break
        if not resource:
            resource = Resource(response.effective_url, content_type)

        self._cache[url] = resource
        self._cache[resource.url] = resource
        return resource

    @staticmethod
    async def fetch(url: str) -> HTTPResponse:
        """Fetch resource with exception handling.

        Error handling as explained in :meth:`Analyzer.analyze`.
        """
        request = 'GET {}'.format(url)
        try:
            # TODO: handle ValueError (e.g. wrong url scheme)
            return await AsyncHTTPClient().fetch(url)
        except HTTPStreamClosedError:
            raise CommunicationError(os.strerror(errno.ESHUTDOWN), request)
        except HTTPTimeoutError:
            raise CommunicationError(os.strerror(errno.ETIMEDOUT), request)
        except HTTPClientError as e:
            if e.code in (404, 410):
                raise AnalysisError('Resource not found [no_resource]', url)
            if e.code in (401, 402, 403, 405, 451):
                raise AnalysisError('Resource forbidden [forbidden_resource]', url)
            raise CommunicationError('Server responded with status {}'.format(e.code), request,
                                     str(e.code))
        except OSError as e:
            raise CommunicationError(str(e), request)


def handle_image(url: str, content_type: str, data: bytes) -> Optional[Image]:
    if content_type in IMAGE_TYPES:
        return Image(url, content_type)
    return None

def handle_webpage(url: str, content_type: str, data: bytes) -> Optional[Resource]:
    # TODO implement (see resolve)
    # if data is somehow invalid:
    # raise AnalysisError('Broken HTML [bad_resource]', url) #.format(url))
    if content_type in WEBPAGE_TYPES:
        return Resource(url, content_type)
    return None

#async def handle_youtube(url: str, content_type: str, data: bytes) -> Optional[Resource]:
#    id = re.find(url, 'foo')
#    response = await fetch('https://api.youtube.com/videos/{}'.format(id))
#    return Video(url)

class AnalysisError(Exception):
    """See :ref:`AnalysisError`.

    Returned if analyzing a web resource fails.

    .. describe:: url

       URL of the web resource subject to analysis.
    """
    args = None # type: Tuple[str, str]

    def __init__(self, message: str, url: str) -> None:
        super().__init__(message)
        self.url = url

    def json(self) -> Dict[str, object]:
        return {**super().json(), 'url': self.url}
