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

"""Test utilites."""

from urllib.parse import urljoin

from tornado.httpclient import AsyncHTTPClient
from tornado.testing import AsyncTestCase

from .jsonredis import JSONRedis
from .micro import (Activity, Application, Collection, Editable, Object, Orderable, Settings,
                    Trashable)
from .util import randstr

class ServerTestCase(AsyncTestCase):
    """Subclass API: Server test case.

    .. attribute:: server

       :class:`server.Server` under test. Must be set by subclass.

    .. attribute:: client_user

       :class:`User` interacting with the server. May be set by subclass.
    """

    def setUp(self):
        super().setUp()
        self.server = None
        self.client_user = None

    def request(self, url, **args):
        """Run a request against the given *url* path.

        The request is issued by :attr:`client_user`, if set. This is a convenient wrapper around
        :meth:`tornado.httpclient.AsyncHTTPClient.fetch` and *args* are passed through.
        """
        headers = args.pop('headers', {})
        if self.client_user:
            headers.update({'Cookie': 'auth_secret=' + self.client_user.auth_secret})
        return AsyncHTTPClient().fetch(urljoin(self.server.url, url), headers=headers, **args)

class CatApp(Application):
    """Simple application for testing purposes.

    .. attribute:: cats

       Map of all :class:`CatApp.Cats`.
    """

    class Cats(Collection, Orderable):
        """Map of all cats."""

        def create(self, name=None):
            """Create a :class:`Cat`."""
            id = 'Cat:{}'.format(randstr())
            cat = Cat(id, self.app, authors=[], trashed=False, name=name,
                      activity=Activity('{}.activity'.format(id), self.app, subscriber_ids=[]))
            self.app.r.oset(cat.id, cat)
            self.app.r.rpush('cats', cat.id)
            return cat

    def __init__(self, redis_url=''):
        super().__init__(redis_url=redis_url)
        self.types.update({'Cat': Cat})
        self.cats = self.Cats((self, 'cats'))

    def do_update(self):
        r = JSONRedis(self.r.r)
        r.caching = False

        # Deprecated since 0.14.0
        cat = r.oget('Cat')
        if cat and 'activity' not in cat:
            cat['activity'] = Activity('Cat.activity', app=self, subscriber_ids=[]).json()
            r.oset(cat['id'], cat)

    def create_settings(self):
        # pylint: disable=unexpected-keyword-arg; decorated
        return Settings(
            id='Settings', app=self, authors=[], title='CatApp', icon=None, icon_small=None,
            icon_large=None, provider_name=None, provider_url=None, provider_description={},
            feedback_url=None, staff=[], push_vapid_private_key=None, push_vapid_public_key=None,
            v=2)

    def sample(self):
        """Set up some sample data."""
        user = self.login()
        auth_request = user.set_email('happy@example.org')
        self.r.set('auth_request', auth_request.id)
        self.cats.create()

class Cat(Object, Editable, Trashable):
    """Cute cat."""

    def __init__(self, id, app, authors, trashed, name, activity):
        super().__init__(id, app)
        Editable.__init__(self, authors, activity)
        Trashable.__init__(self, trashed, activity)
        self.name = name
        self.activity = activity
        self.activity.host = self

    def do_edit(self, **attrs):
        if 'name' in attrs:
            self.name = attrs['name']

    def json(self, restricted=False, include=False):
        return {
            **super().json(restricted, include),
            **Editable.json(self, restricted, include),
            **Trashable.json(self, restricted, include),
            'name': self.name,
            'activity': self.activity.json(restricted)
        }
