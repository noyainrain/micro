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

# pylint: disable=missing-docstring; test module

import http.client
import json

from tornado.httpclient import HTTPError
from tornado.testing import gen_test

from micro.server import Server, make_orderable_endpoints, make_trashable_endpoints
from micro.test import ServerTestCase, CatApp

class ServerTest(ServerTestCase):
    def setUp(self):
        super().setUp()
        self.app = CatApp(redis_url='15')
        self.app.r.flushdb()
        handlers = [
            *make_orderable_endpoints(r'/api/cats', lambda: self.app.cats),
            *make_trashable_endpoints(r'/api/cats/([^/]+)', lambda i: self.app.cats[i])
        ]
        self.server = Server(self.app, handlers, client_path='hello',
                             client_modules_path='node_modules', port=16160)
        self.server.start()
        self.staff_member = self.app.login()
        self.user = self.app.login()
        self.client_user = self.user

    @gen_test
    def test_availability(self):
        # UI
        yield self.request('/')
        yield self.request(
            '/log-client-error', method='POST',
            body='{"type": "Error", "stack": "micro.UI.prototype.createdCallback", "url": "/"}')

        # API
        yield self.request('/api/login', method='POST', body='')
        yield self.request('/api/users/' + self.user.id)
        yield self.request('/api/users/' + self.user.id, method='POST', body='{"name": "Happy"}')
        yield self.request('/api/settings')

        # API (generic)
        cat = self.app.cats.create()
        yield self.request('/api/cats/move', method='POST',
                           body='{{"item_id": "{}", "to_id": null}}'.format(cat.id))
        yield self.request('/api/cats/{}/trash'.format(cat.id), method='POST', body='')
        yield self.request('/api/cats/{}/restore'.format(cat.id), method='POST', body='')

        # API (as staff member)
        self.client_user = self.staff_member
        yield self.request(
            '/api/settings', method='POST',
            body='{"title": "CatzApp", "icon": "http://example.org/static/icon.svg"}')
        yield self.request('/api/activity')

    @gen_test
    def test_get_user(self):
        response = yield self.request('/api/users/' + self.user.id)
        meeting = json.loads(response.body.decode())
        self.assertEqual(meeting.get('__type__'), 'User')

    @gen_test
    def test_get_user_id_nonexistent(self):
        with self.assertRaises(HTTPError) as cm:
            yield self.request('/api/users/foo')
        self.assertEqual(cm.exception.code, http.client.NOT_FOUND)

    @gen_test
    def test_post_user_body_invalid_json(self):
        with self.assertRaises(HTTPError) as cm:
            yield self.request('/api/users/' + self.user.id, method='POST', body='foo')
        e = cm.exception
        self.assertEqual(e.code, http.client.BAD_REQUEST)

    @gen_test
    def test_post_user_name_bad_type(self):
        with self.assertRaises(HTTPError) as cm:
            yield self.request('/api/users/' + self.user.id, method='POST', body='{"name": 42}')
        self.assertEqual(cm.exception.code, http.client.BAD_REQUEST)
        error = json.loads(cm.exception.response.body.decode())
        self.assertEqual(error.get('__type__'), 'InputError')

    @gen_test
    def test_post_settings_provider_description_bad_type(self):
        with self.assertRaises(HTTPError) as cm:
            yield self.request('/api/settings', method='POST',
                               body='{"provider_description": {"en": " "}}')
        self.assertEqual(cm.exception.code, http.client.BAD_REQUEST)
        self.assertIn('provider_description_bad_type', cm.exception.response.body.decode())
