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

"""Functionality for handling web resource.

.. data:: HandleResourceFunc

   Function of the form
   ``handle(url: str, content_type: str, data: bytes, analyzer: Analyzer) -> Optional[Resource]``
   which processes a web resource and returns a description of it. Resource *url* media type
   *content_type* and content *data*. Additionally *analyzer*, useful for analyzing subresources. If
   the given resource cannot be handled by the function, ``None`` is returned. May be ``async``.
"""

from collections import OrderedDict
import errno
from html.parser import HTMLParser
from inspect import isawaitable
import os
import time
from typing import Awaitable, Callable, Dict, List, Optional, Tuple, Union, cast
from urllib.parse import urljoin

from tornado.httpclient import AsyncHTTPClient, HTTPClientError, HTTPResponse
from tornado.simple_httpclient import HTTPStreamClosedError, HTTPTimeoutError

from . import error
from .error import CommunicationError, Error
from .util import str_or_none

HandleResourceFunc = Callable[[str, str, bytes, 'Analyzer'],
                              Union[Optional['Resource'], Awaitable[Optional['Resource']]]]

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

       List of web resource handlers to use for analyzing. By default, all handlers included with
       the module are enabled.
    """

    _CACHE_SIZE = 128
    _CACHE_TTL = 60 * 60

    def __init__(self, *, handlers: List[HandleResourceFunc] = None, _stack: List[str] = None,
                 _cache: 'OrderedDict[str, Tuple[Resource, float]]' = None) -> None:
        self.handlers = ([handle_image, handle_webpage] if handlers is None
                         else list(handlers)) # type: List[HandleResourceFunc]
        self._stack = [] if _stack is None else _stack
        self._cache = OrderedDict() if _cache is None else _cache

    async def analyze(self, url: str) -> Resource:
        """Analyze the web resource at *url* and return a description of it.

        *url* is an absolute HTTP(S) URL. If there is a problem fetching or analyzing the resource,
        a :class:`CommunicationError` or :class:`AnalysisError` is raised respectively.

        Results are cached for around one hour.
        """
        if len(self._stack) == 3:
            raise _LoopError()

        try:
            return self._cache_get(url)
        except KeyError:
            pass

        response = await self.fetch(url)
        content_type = response.headers['Content-Type'].split(';', 1)[0]
        analyzer = Analyzer(handlers=self.handlers, _stack=self._stack + [url], _cache=self._cache)
        resource = None

        for handle in self.handlers:
            try:
                result = handle(response.effective_url, content_type, response.body, analyzer)
                resource = (await cast(Awaitable[Optional[Resource]], result) if isawaitable(result)
                            else cast(Optional[Resource], result))
            except _LoopError:
                if self._stack:
                    raise
                raise BrokenResourceError('Loop analyzing {}'.format(url))
            if resource is not None:
                break
        if resource is None:
            resource = Resource(response.effective_url, content_type)

        self._cache_set(url, resource)
        self._cache_set(resource.url, resource)
        return resource

    def _cache_get(self, url: str) -> Resource:
        resource, expires = self._cache[url]
        if time.time() >= expires:
            del self._cache[url]
            raise KeyError(url)
        return resource

    def _cache_set(self, url: str, resource: Resource) -> None:
        try:
            del self._cache[url]
        except KeyError:
            pass
        if len(self._cache) == self._CACHE_SIZE:
            self._cache.popitem(last=False)
        self._cache[url] = (resource, time.time() + self._CACHE_TTL)

    async def fetch(self, request: str, **kwargs: object) -> HTTPResponse:
        """Execute a *request*.

        Wrapper around :meth:`AsyncHTTPClient.fetch` with error handling suitable for
        :meth:`analyze`.
        """
        try:
            return await AsyncHTTPClient().fetch(request)
        except ValueError:
            raise error.ValueError('Bad url scheme {!r}'.format(request, **kwargs))
        except HTTPStreamClosedError:
            raise CommunicationError('{} for GET {}'.format(os.strerror(errno.ESHUTDOWN), request))
        except HTTPTimeoutError:
            raise CommunicationError('{} for GET {}'.format(os.strerror(errno.ETIMEDOUT), request))
        except HTTPClientError as e:
            if e.code in (404, 410):
                raise NoResourceError('No resource at {}'.format(request))
            if e.code in (401, 402, 403, 405, 451):
                raise ForbiddenResourceError('Forbidden resource at {}'.format(request))
            raise CommunicationError('Unexpected response status {} for GET {}'.format(e.code, request))
        except OSError as e:
            raise CommunicationError('{} for GET {}'.format(e, request))

def handle_image(url: str, content_type: str, data: bytes, analyzer: Analyzer) -> Optional[Image]:
    """Process an image resource."""
    # pylint: disable=unused-argument; part of API
    if content_type in ['image/jpeg', 'image/png', 'image/svg+xml', 'image/gif']:
        return Image(url, content_type)
    return None

async def handle_webpage(url: str, content_type: str, data: bytes,
                         analyzer: Analyzer) -> Optional[Resource]:
    """Process a webpage resource."""
    if content_type not in ['text/html', 'application/xhtml+xml']:
        return None
    try:
        html = data.decode()
    except UnicodeDecodeError:
        raise BrokenResourceError('Bad data encoding analyzing {}'.format(url))
    parser = _MetaParser()
    parser.feed(html)
    parser.close()

    # https://developer.mozilla.org/en-US/docs/Web/HTML/Element/meta
    # http://ogp.me/
    title = str_or_none(parser.meta.get('og:title') or parser.meta.get('title') or '')
    short = str_or_none(parser.meta.get('og:description') or parser.meta.get('description') or '')
    description = '{} - {}'.format(title, short) if title and short else title or short

    image = None
    image_url = (parser.meta.get('og:image') or parser.meta.get('og:image:url') or
                 parser.meta.get('og:image:secure_url'))
    if image_url:
        image_url = urljoin(url, image_url)
        try:
            res = await analyzer.analyze(image_url)
        except error.ValueError:
            raise BrokenResourceError('Bad data image URL scheme {!r} analyzing {}'.format(image_url, url))
        if not isinstance(res, Image):
            raise BrokenResourceError('Bad image type {!r} analyzing {}'.format(type(res).__name__, url))
        image = res

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
