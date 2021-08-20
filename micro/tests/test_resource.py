# micro
# Copyright (C) 2021 micro contributors
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

# pylint: disable=missing-docstring; test module

from io import BytesIO
from tempfile import mkdtemp

import PIL
from tornado.testing import AsyncTestCase, AsyncHTTPTestCase, gen_test
from tornado.web import Application, RequestHandler

from micro import tests
from micro.resource import (Analyzer, BrokenResourceError, Files, ForbiddenResourceError, Image,
                            NoResourceError, Resource)
from micro.webapi import CommunicationError

class AnalyzerTestCase(AsyncHTTPTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.analyzer = Analyzer(files=Files(mkdtemp()))

    def get_app(self) -> Application:
        return Application([(r'/codes/([^/]+)$', CodeEndpoint)], # type: ignore[misc]
                           static_path=tests.RES_PATH)

    @gen_test # type: ignore[misc]
    async def test_analyze_blob(self) -> None:
        resource = await self.analyzer.analyze(self.get_url('/static/blob'))
        self.assertIsInstance(resource, Resource)
        self.assertRegex(resource.url, r'/static/blob$')
        self.assertEqual(resource.content_type, 'application/octet-stream')
        self.assertIsNone(resource.description)
        self.assertIsNone(resource.thumbnail)

    @gen_test # type: ignore[misc]
    async def test_analyze_image(self) -> None:
        # Cat August 2010-4 by Joaquim Alves Gaspar
        # (https://commons.wikimedia.org/wiki/File:Cat_August_2010-4.jpg)
        image = await self.analyzer.analyze(self.get_url('/static/image.jpg'))
        self.assertIsInstance(image, Image)
        self.assertEqual(image.content_type, 'image/jpeg')
        self.assertIsNone(image.description)
        self.assertTrue(image.thumbnail)

    @gen_test # type: ignore[misc]
    async def test_analyze_webpage(self) -> None:
        webpage = await self.analyzer.analyze(self.get_url('/static/webpage.html'))
        self.assertIsInstance(webpage, Resource)
        self.assertEqual(webpage.content_type, 'text/html')
        self.assertEqual(webpage.description, 'Happy Blog')
        self.assertTrue(webpage.thumbnail)

    @gen_test # type: ignore[misc]
    async def test_analyze_file(self) -> None:
        assert self.analyzer.files
        url = await self.analyzer.files.write(b'Meow!', 'text/plain')
        resource = await self.analyzer.analyze(url)
        self.assertEqual(resource.url, url)
        self.assertEqual(resource.content_type, 'text/plain')

    @gen_test # type: ignore[misc]
    async def test_analyze_no_resource(self) -> None:
        with self.assertRaises(NoResourceError):
            await self.analyzer.analyze(self.get_url('/foo'))

    @gen_test # type: ignore[misc]
    async def test_analyze_forbidden_resource(self) -> None:
        with self.assertRaises(ForbiddenResourceError):
            await self.analyzer.analyze(self.get_url('/codes/403'))

    @gen_test # type: ignore[misc]
    async def test_analyze_error_response(self) -> None:
        with self.assertRaises(CommunicationError):
            await self.analyzer.analyze(self.get_url('/codes/500'))

    @gen_test # type: ignore[misc]
    async def test_analyze_no_host(self) -> None:
        with self.assertRaises(CommunicationError):
            await self.analyzer.analyze('https://[::]/')

    @gen_test # type: ignore[misc]
    async def test_thumbnail(self) -> None:
        with open(tests.RES_PATH / 'image.jpg', 'rb') as f:
            thumbnail = await self.analyzer.thumbnail(f.read(), 'image/jpeg')
        assert self.analyzer.files
        data, content_type = await self.analyzer.files.read(thumbnail.url)
        with PIL.Image.open(BytesIO(data)) as image:
            self.assertEqual(image.size, (1177, 720))
        self.assertEqual(content_type, 'image/jpeg')

    @gen_test # type: ignore[misc]
    async def test_thumbnail_svg(self) -> None:
        thumbnail = await self.analyzer.thumbnail(b'<svg xmlns="http://www.w3.org/2000/svg" />',
                                                  'image/svg+xml')
        assert self.analyzer.files
        data, _ = await self.analyzer.files.read(thumbnail.url)
        self.assertEqual(data, b'<svg xmlns="http://www.w3.org/2000/svg" />')

    @gen_test # type: ignore[misc]
    async def test_thumbnail_decompression_bomb(self) -> None:
        # decompression_bomb.gif by Alex Clark and Pillow contributors
        # (https://github.com/python-pillow/Pillow/blob/master/Tests/images/decompression_bomb.gif)
        with (tests.RES_PATH / 'bomb.gif').open('rb') as f:
            data = f.read()
        with self.assertRaisesRegex(BrokenResourceError, 'data'):
            await self.analyzer.thumbnail(data, 'image/gif')

    @gen_test # type: ignore[misc]
    async def test_thumbnail_bad_data(self) -> None:
        with self.assertRaisesRegex(BrokenResourceError, 'data'):
            await self.analyzer.thumbnail(b'foo', 'image/jpeg')

class FilesTest(AsyncTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.files = Files(mkdtemp())

    @gen_test # type: ignore[misc]
    async def test_read(self) -> None:
        url = await self.files.write(b'Meow!', 'text/plain')
        data, content_type = await self.files.read(url)
        self.assertEqual(data, b'Meow!')
        self.assertEqual(content_type, 'text/plain')

    @gen_test # type: ignore[misc]
    async def test_read_no(self) -> None:
        with self.assertRaises(LookupError):
            await self.files.read('file:/foo.txt')

    @gen_test # type: ignore[misc]
    async def test_garbage_collect(self) -> None:
        urls = [await self.files.write(data, 'application/octet-stream')
                for data in (b'a', b'b', b'c', b'd')]
        n = await self.files.garbage_collect(urls[:2])
        self.assertEqual(n, 2)
        data, _ = await self.files.read(urls[0])
        self.assertEqual(data, b'a')
        data, _ = await self.files.read(urls[1])
        self.assertEqual(data, b'b')
        with self.assertRaises(LookupError):
            await self.files.read(urls[2])
        with self.assertRaises(LookupError):
            await self.files.read(urls[3])

class CodeEndpoint(RequestHandler):
    # pylint: disable=abstract-method; Tornado handlers define a semi-abstract data_received()

    def get(self, code: str) -> None:
        # pylint: disable=arguments-differ; Tornado handler arguments are defined by URLs
        self.set_status(int(code))
