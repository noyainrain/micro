# micro
# Copyright (C) 2018 micro contributors
#
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU
# Lesser General Public License as published by the Free Software Foundation, either version 3 of
# the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without
# even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License along with this program.
# If not, see <http://www.gnu.org/licenses/>.

"""Functionality for handling web resources.

.. data:: HandleResourceFunc

   Function of the form ``handle(url, content_type, data, analyzer)`` which processes a web resource
   and returns a description of it. The resource is given by its *url*, *content_type* and content
   *data*. Additionally, the active *analyzer* is available, useful to :meth:`Analyzer.analyze`
   subresources. If the function cannot handle the resource in question, ``None`` is returned. May
   be ``async``.
"""

from collections import OrderedDict
from datetime import datetime, timedelta
import errno
from html.parser import HTMLParser
from inspect import isawaitable
import os
from typing import Awaitable, Callable, Dict, List, Optional, Tuple, Union, cast
from urllib.parse import urljoin

from tornado.httpclient import AsyncHTTPClient, HTTPClientError, HTTPResponse
from tornado.simple_httpclient import HTTPStreamClosedError, HTTPTimeoutError

from . import error
from .error import CommunicationError, Error
from .util import str_or_none

HandleResourceFunc = Callable[[str, str, bytes, 'Analyzer'],
                              Union[Optional['Resource'], Awaitable[Optional['Resource']]]]

from micro.jsonredis import expect_type, expect_type2

class Resource:
    """See :ref:`Resource`."""

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

    @staticmethod
    def parse(data: Dict[str, object]) -> 'Resource':
        url = expect_type(str)(data['url'])
        content_type = expect_type(str)(data['content_type'])
        description = expect_type2(str)(data['description'])
        return Resource(url, content_type, description=description)

    def json(self) -> Dict[str, object]:
        """Return a JSON representation of the resource."""
        return {
            '__type__': type(self).__name__,
            'url': self.url,
            'content_type': self.content_type,
            'description': self.description,
            'image': self.image.json() if self.image else None
        }

class Image(Resource):
    """See :ref:`Image`."""

    def __init__(self, url: str, content_type: str, *, description: str = None) -> None:
        super().__init__(url, content_type, description=description)

class Analyzer:
    """Web resource analyzer.

    .. attribute:: handlers

       List of web resource handlers to use for analyzing. By default all handlers included with the
       module are enabled.
    """

    _CACHE_SIZE = 128
    _CACHE_TTL = timedelta(hours=1)

    def __init__(
            self, *, handlers: List[HandleResourceFunc] = None,
            _cache: 'OrderedDict[str, Tuple[Resource, datetime]]' = None,
            _stack: List[str] = None) -> None:
        self.handlers = ([handle_image, handle_webpage] if handlers is None
                         else list(handlers)) # type: List[HandleResourceFunc]
        self._cache = OrderedDict() if _cache is None else _cache
        self._stack = [] if _stack is None else _stack

    async def analyze(self, url: str) -> Resource:
        """Analyze the web resource at *url* and return a description of it.

        *url* is an absolute HTTP(S) URL. If there is a problem fetching or analyzing the resource,
        a :exc:`CommunicationError` or :exc:`AnalysisError` is raised respectively.

        Results are cached for about one hour.
        """
        if len(self._stack) == 3:
            raise _LoopError()

        try:
            return self._get_cache(url)
        except KeyError:
            pass

        response = await self.fetch(url)
        content_type = response.headers['Content-Type'].split(';', 1)[0]

        resource = None
        analyzer = Analyzer(handlers=self.handlers, _cache=self._cache, _stack=self._stack + [url])
        for handle in self.handlers:
            try:
                result = handle(response.effective_url, content_type, response.body, analyzer)
                resource = (await cast(Awaitable[Optional[Resource]], result) if isawaitable(result)
                            else cast(Optional[Resource], result))
            except _LoopError:
                if self._stack:
                    raise
                raise BrokenResourceError('Loop analyzing {}'.format(url)) from None
            if resource:
                break
        if not resource:
            resource = Resource(response.effective_url, content_type)

        self._set_cache(url, resource)
        self._set_cache(resource.url, resource)
        return resource

    async def fetch(self, request: str) -> HTTPResponse:
        """Execute a *request*.

        Utility wrapper around :meth:`AsyncHTTPClient.fetch` with error handling suitable for
        :meth:`analyze`.
        """
        try:
            return await AsyncHTTPClient().fetch(request)
        except ValueError:
            raise error.ValueError('Bad url scheme {!r}'.format(request))
        except HTTPStreamClosedError:
            raise CommunicationError('{} for GET {}'.format(os.strerror(errno.ESHUTDOWN), request))
        except HTTPTimeoutError:
            raise CommunicationError('{} for GET {}'.format(os.strerror(errno.ETIMEDOUT), request))
        except HTTPClientError as e:
            if e.code in (404, 410):
                raise NoResourceError('No resource at {}'.format(request))
            if e.code in (401, 402, 403, 405, 451):
                raise ForbiddenResourceError('Forbidden resource at {}'.format(request))
            raise CommunicationError(
                'Unexpected response status {} for GET {}'.format(e.code, request))
        except OSError as e:
            raise CommunicationError('{} for GET {}'.format(e, request))

    def _get_cache(self, url: str) -> Resource:
        resource, expires = self._cache[url]
        if datetime.utcnow() >= expires:
            del self._cache[url]
            raise KeyError(url)
        return resource

    def _set_cache(self, url: str, resource: Resource) -> None:
        try:
            del self._cache[url]
        except KeyError:
            pass
        if len(self._cache) == self._CACHE_SIZE:
            self._cache.popitem(last=False)
        self._cache[url] = (resource, datetime.utcnow() + self._CACHE_TTL)

def handle_image(url: str, content_type: str, data: bytes, analyzer: Analyzer) -> Optional[Image]:
    """Process an image resource."""
    # pylint: disable=unused-argument; part of API
    # https://en.wikipedia.org/wiki/Comparison_of_web_browsers#Image_format_support
    if content_type in {'image/bmp', 'image/gif', 'image/jpeg', 'image/png', 'image/svg+xml'}:
        return Image(url, content_type)
    return None

async def handle_webpage(url: str, content_type: str, data: bytes,
                         analyzer: Analyzer) -> Optional[Resource]:
    """Process a webpage resource."""
    if content_type not in {'text/html', 'application/xhtml+xml'}:
        return None

    try:
        html = data.decode()
    except UnicodeDecodeError:
        raise BrokenResourceError('Bad data encoding analyzing {}'.format(url))
    parser = _MetaParser()
    parser.feed(html)
    parser.close()

    title = str_or_none(parser.meta.get('og:title') or parser.meta.get('title') or '')
    text = str_or_none(parser.meta.get('og:description') or parser.meta.get('description') or '')
    description = '{} - {}'.format(title, text) if title and text else title or text

    image = None
    image_url = (parser.meta.get('og:image') or parser.meta.get('og:image:url') or
                 parser.meta.get('og:image:secure_url'))
    if image_url:
        image_url = urljoin(url, image_url)
        try:
            resource = await analyzer.analyze(image_url)
        except error.ValueError:
            raise BrokenResourceError(
                'Bad data image URL scheme {!r} analyzing {}'.format(image_url, url))
        if not isinstance(resource, Image):
            raise BrokenResourceError(
                'Bad image type {!r} analyzing {}'.format(type(resource).__name__, url))
        image = resource

    return Resource(url, content_type, description=description, image=image)

class AnalysisError(Error):
    """See :ref:`AnalysisError`."""
    pass

class NoResourceError(AnalysisError):
    """See :ref:`NoResourceError`."""
    pass

class ForbiddenResourceError(AnalysisError):
    """See :ref:`ForbiddenResourceError`."""
    pass

class BrokenResourceError(AnalysisError):
    """See :ref:`BrokenResourceError`."""
    pass

class _LoopError(Exception):
    pass

class _MetaParser(HTMLParser):
    # pylint: disable=abstract-method; https://bugs.python.org/issue31844

    def __init__(self) -> None:
        super().__init__()
        self.meta = {} # type: Dict[str, str]
        self._read_tag_data = None # type: Optional[str]

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, str]]) -> None:
        if not self._read_tag_data:
            if tag == 'title':
                self.meta['title'] = ''
                self._read_tag_data = 'title'
            elif tag == 'meta':
                # Consider standard HTML (name) and Open Graph / RDFa (property) tags
                key = next((v for k, v in attrs if k in {'name', 'property'}), None)
                value = next((v for k, v in attrs if k == 'content'), None)
                if key is not None and value is not None:
                    self.meta[key] = value

    def handle_endtag(self, tag: str) -> None:
        if self._read_tag_data == tag:
            self._read_tag_data = None

    def handle_data(self, data: str) -> None:
        if self._read_tag_data:
            self.meta[self._read_tag_data] += data
