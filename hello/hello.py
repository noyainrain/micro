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

"""micro application example."""

import sys

import micro
from micro import Application, Collection, Editable, Object, Settings
from micro.jsonredis import RedisList
from micro.server import CollectionEndpoint, Server
from micro.util import make_command_line_parser, randstr, setup_logging, str_or_none

class Hello(Application):
    """Hello application.

    .. attribute:: greetings

       See :class:`Hello.Greetings`.
    """

    class Greetings(Collection):
        """Collection of all class:`Greeting`s."""

        # TODO: text optional?
        async def create(self, text, *, entity=None):
            """Create a :class:`Greeting` and return it."""
            text = str_or_none(text)
            if entity is not None:
                entity = await self.resolve_entity(entity)
            if text is None and entity is None:
                raise micro.ValueError('text_entity_none')

            greeting = Greeting(id='Greeting:{}'.format(randstr()), app=self.app,
                                authors=[self.app.user.id], text=text, entity=entity)
            self.r.oset(greeting.id, greeting)
            self.r.rpush(self.ids.key, greeting.id)
            return greeting

    def __init__(self, redis_url='', email='bot@localhost', smtp_url='',
                 render_email_auth_message=None):
        super().__init__(redis_url, email, smtp_url, render_email_auth_message)
        self.types.update({'Greeting': Greeting})
        self.greetings = Hello.Greetings(RedisList('greetings', self.r.r), app=self)

    def create_settings(self):
        # pylint: disable=unexpected-keyword-arg; decorated
        return Settings(
            id='Settings', app=self, authors=[], title='Hello', icon=None, icon_small=None,
            icon_large=None, provider_name=None, provider_url=None, provider_description={},
            feedback_url=None, staff=[], push_vapid_private_key=None, push_vapid_public_key=None,
            v=2)

class Greeting(Object, Editable):
    """Public greeting.

    .. attribute:: text

       Text content.
    """

    def __init__(self, id, app, authors, text, entity):
        super().__init__(id, app)
        Editable.__init__(self, authors)
        self.text = text
        self.entity = entity

    async def do_edit(self, **attrs):
        text = str_or_none(attrs['text']) if 'text' in attrs else self.text
        entity = self.entity
        if 'entity' in attrs:
            entity = attrs['entity']
            if entity is not None:
                entity = await self.resolve_entity(entity)
        if text is None and entity is None:
            raise micro.ValueError('text_entity_none')

        if 'text' in attrs:
            self.text = text
        if 'entity' in attrs:
            self.entity = entity

    def json(self, restricted=False, include=False):
        return {
            **super().json(restricted, include),
            **Editable.json(self, restricted, include),
            'text': self.text,
            'entity': self.entity.json() if self.entity else None
        }

def make_server(port=8080, url=None, client_path='.', debug=False, redis_url='', smtp_url='',
                client_map_service_key=None):
    """Create a Hello server."""
    app = Hello(redis_url, smtp_url=smtp_url)
    handlers = [
        (r'/api/greetings$', _GreetingsEndpoint, {'get_collection': lambda *args: app.greetings})
    ]
    return Server(app, handlers, port, url, client_path, client_modules_path='node_modules',
                  debug=debug, client_map_service_key=client_map_service_key)

class _GreetingsEndpoint(CollectionEndpoint):
    # pylint: disable=abstract-method; Tornado handlers define a semi-abstract data_received()
    # pylint: disable=arguments-differ; Tornado handler arguments are defined by URLs

    async def post(self):
        args = self.check_args({'text': (str, None), 'entity': (str, None, 'opt')})
        greeting = await self.app.greetings.create(**args)
        self.write(greeting.json(restricted=True, include=True))

def main(args):
    """Run Hello.

    *args* is the list of command line arguments.
    """
    args = make_command_line_parser().parse_args(args[1:])
    setup_logging(args.debug if 'debug' in args else False)
    make_server(**vars(args)).run()
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
