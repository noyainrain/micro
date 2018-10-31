# TODO

import errno
import os
from typing import Dict, List, Tuple, Callable, Optional, cast, Awaitable, Union

from . import error
from .error import CommunicationError, Error
from .util import str_or_none

from tornado.httpclient import AsyncHTTPClient, HTTPClientError, HTTPResponse
from tornado.simple_httpclient import HTTPStreamClosedError, HTTPTimeoutError

IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/svg+xml', 'image/gif']
WEBPAGE_TYPES = ['text/html', 'application/xhtml+xml']

HandleFunc = Callable[[str, str, bytes, 'Analyzer'],
                      Union[Optional['Resource'], Awaitable[Optional['Resource']]]]

class Resource:
    """TODO Web resource representation with useful meta data."""

    def __init__(self, url: str, content_type: str, *, description: str = None,
                 image: 'Image' = None) -> None:
        if str_or_none(url) is None:
            raise error.ValueError('Blank url')
        if str_or_none(content_type) is None:
            raise error.ValueError('Blank content_type')
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

from inspect import isawaitable

class Analyzer:
    """TODO.

    .. attribute:: handlers

       TODO. Defaults to all builtin handlers.
    """

    def __init__(self, *, handlers: List[HandleFunc] = None, _stack: List[str] = []) -> None:
        self.handlers = ([handle_image, handle_webpage] if handlers is None
                         else list(handlers)) # type: List[HandleFunc]
        self._stack = list(_stack)
        self._cache = {} # type: Dict[str, Resource]
        #self._expiry = deque()

    #def _clear_cache(self):
    #    now = time.time()
    #    for x in self._expiry:
    #        if x[0] > now:
    #            break
    #        del self._cache[x[1]]
    #        self._expiry.popleft()

    async def analyze(self, url: str) -> Resource:
        """Analyze the resource at *url*.

        CommunicationError, AnalysisError.
        """
        #self._clear_cache()
        if url in self._cache:
            return self._cache[url]

        if len(self._stack) >= 3:
            raise BadDataError('max sub resources', url)
        analyzer = Analyzer(handlers=self.handlers, _stack=self._stack + [url])

        request = 'GET {}'.format(url)
        try:
            response = await AsyncHTTPClient().fetch(url)
        except ValueError:
            raise error.ValueError('Unsupported url {}'.format(url))
        except HTTPStreamClosedError:
            raise CommunicationError(os.strerror(errno.ESHUTDOWN), request)
        except HTTPTimeoutError:
            raise CommunicationError(os.strerror(errno.ETIMEDOUT), request)
        except HTTPClientError as e:
            if e.code in (404, 410):
                raise NoResourceError('Resource not found', url)
            if e.code in (401, 402, 403, 405, 451):
                raise ForbiddenResourceError('Resource forbidden', url)
            raise CommunicationError('Server responded with status {}'.format(e.code), request,
                                     str(e.code))
        except OSError as e:
            raise CommunicationError(str(e), request)
        content_type = response.headers['Content-Type'].split(';', 1)[0]

        resource = None
        for handle in self.handlers:
            result = handle(response.effective_url, content_type, response.body, analyzer)
            resource = result if result is None or isinstance(result, Resource) else await result
            #resource = await result if isawaitable(result) else result
            #resource = handle(response.effective_url, content_type, response.body)
            #if resource is not None and not isinstance(resource, Resource): # isawaitable(resource):
            #    resource = await resource
            if resource is not None:
                break
        # assert resource is None or isinstance(resource, Resource)
        if resource is None:
            resource = Resource(response.effective_url, content_type)

        self._cache[url] = resource
        self._cache[resource.url] = resource
        #expire = time.time() + 60 * 60
        #self._expiry.append((expire, url))
        #self._expiry.append((expire, resource.url))
        return resource

    @staticmethod
    async def fetch(url: str) -> HTTPResponse:
        """Fetch resource with exception handling.

        Error handling as explained in :meth:`Analyzer.analyze`.
        """

from html.parser import HTMLParser

def handle_image(url: str, content_type: str, data: bytes, analyzer: Analyzer) -> Optional[Image]:
    if content_type in IMAGE_TYPES:
        return Image(url, content_type)
    return None

from micro.util import str_or_none
from urllib.parse import urljoin

async def handle_webpage(url: str, content_type: str, data: bytes,
                         analyzer: Analyzer) -> Optional[Resource]:
    # TODO implement (see resolve)
    # if data is somehow invalid:
    # raise AnalysisError('Broken HTML [bad_resource]', url) #.format(url))
    if content_type not in WEBPAGE_TYPES:
        return None
        #raise AnalysisError('Unsupported content type {} [unsupported_content_type]'.format(content_type), url)
        #raise AnalysisError('content_type: unsupported' 'content type {} [unsupported_content_type]'.format(content_type), url)
        #raise ValueError('content_type', 'unsupported', content_type)
        #raise ValueError('Unsupported content_type {}'.format(content_type))
        #raise AnalysisError('Unsupported content_type {}'.format(content_type), url)
    try:
        html = data.decode()
    except UnicodeDecodeError:
        raise BadDataError('unicode', url)
    parser = _MetaParser()
    parser.feed(html)
    parser.close()

    # https://developer.mozilla.org/en-US/docs/Web/HTML/Element/meta
    # http://ogp.me/
    title = str_or_none(parser.meta.get('og:title') or parser.meta.get('title') or '')
    short = str_or_none(parser.meta.get('og:description') or parser.meta.get('description') or '')
    description = '{} - {}'.format(title, short) if title and short else title or short

    image = None
    image_url = parser.meta.get('og:image') or parser.meta.get('og:image:url') or parser.meta.get('og:image:secure_url')
    if image_url:
        image_url = urljoin(url, image_url)
        try:
            res = await analyzer.analyze(image_url)
        except ValueError:
            raise BadDataError('url', image_url)
        if not isinstance(res, Image):
            raise BadDataError('not an image', image_url)
        image = res

    return Resource(url, content_type, description=description, image=image)

#async def handle_youtube(url: str, content_type: str, data: bytes) -> Optional[Resource]:
#    id = re.find(url, 'foo')
#    response = await fetch('https://api.youtube.com/videos/{}'.format(id))
#    return Video(url)

class AnalysisError(Error):
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

class NoResourceError(AnalysisError):
    """TODO."""
    pass

class ForbiddenResourceError(AnalysisError):
    """TODO."""
    pass

class BadDataError(AnalysisError):
    """TODO."""
    pass

# TODO: should we quit after head?
class _MetaParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.meta = {} # type: Dict[str, str]
        self._read = None # type: Optional[str]

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, str]]) -> None:
        if not self._read:
            if tag == 'title':
                self.meta['title'] = ''
                self._read = 'title'
            elif tag == 'meta':
                # HTML and OpenGraph
                key = next((v for k, v in attrs if k in ['name', 'property']), None)
                value = next((v for k, v in attrs if k == 'content'), None)
                if key and value:
                    self.meta[key] = value

    def handle_endtag(self, tag: str) -> None:
        if self._read == tag:
            self._read = None

    def handle_data(self, data: str) -> None:
        if self._read:
            self.meta[self._read] += data
