# TODO

import os

from micro.error import CommunicationError

from micro.resource import Analyzer, AnalysisError, Resource, Image

from tornado.web import Application, RequestHandler
from tornado.testing import AsyncHTTPTestCase, gen_test

class EchoHandler(RequestHandler):
    def get(self, code: str) -> None:
        self.set_status(int(code))

class AnalyzerTestCase(AsyncHTTPTestCase):
    def get_app(self) -> Application:
        return Application(
            [('/echo/([^/]+)$', EchoHandler)],
            static_path=os.path.join(os.path.dirname(__file__), 'res'))

    @gen_test
    async def test_analyze_blob(self) -> None:
        analyzer = Analyzer()
        resource = await analyzer.analyze(self.get_url('/static/blob'))
        self.assertIsInstance(resource, Resource)
        self.assertRegex(resource.url, '/static/blob$')
        self.assertEqual(resource.content_type, 'application/octet-stream')
        self.assertIsNone(resource.description)
        self.assertIsNone(resource.image)

    @gen_test
    async def test_analyze_image(self) -> None:
        analyzer = Analyzer()
        image = await analyzer.analyze(self.get_url('/static/image.png'))
        self.assertIsInstance(image, Image)
        self.assertEqual(image.content_type, 'image/png')

    @gen_test
    async def test_analyze_webpage(self):
        analyzer = Analyzer()
        webpage = await analyzer.analyze(self.get_url('/static/webpage.html'))
        self.assertIsInstance(webpage, Resource)
        # TODO implement and test more
        self.assertEqual(webpage.content_type, 'text/html')

    @gen_test
    async def test_analyze_no_resource(self) -> None:
        analyzer = Analyzer()
        with self.assertRaisesRegex(AnalysisError, r'\[no_resource\]'):
            await analyzer.analyze(self.get_url('/foo'))

    @gen_test
    async def test_analyze_forbidden_resource(self) -> None:
        analyzer = Analyzer()
        with self.assertRaisesRegex(AnalysisError, r'\[forbidden_resource\]'):
            await analyzer.analyze(self.get_url('/echo/403'))

    @gen_test
    async def test_analyze_error_resource(self) -> None:
        analyzer = Analyzer()
        with self.assertRaises(CommunicationError):
            await analyzer.analyze(self.get_url('/echo/500'))

    @gen_test
    async def test_analyze_no_host(self) -> None:
        analyzer = Analyzer()
        with self.assertRaises(CommunicationError):
            await analyzer.analyze('http://example.invalid/')
