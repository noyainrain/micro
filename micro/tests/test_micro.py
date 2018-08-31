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

from subprocess import check_call
from tempfile import mkdtemp
from unittest.mock import patch

from redis import RedisError
from tornado.testing import AsyncTestCase

import micro
from micro import Activity, Event, Location
from micro.test import CatApp, Cat

SETUP_DB_SCRIPT = """\
from micro.test import CatApp
app = CatApp(redis_url='15')
app.r.flushdb()
app.update()
app.sample()

# Compatibility for sample data without a cat (deprecated since 0.6.0)
if not hasattr(app, 'cats'):
    from micro.test import Cat
    app.r.oset('Cat', Cat(id='Cat', trashed=False, app=app, authors=[], name=None))
"""

class MicroTestCase(AsyncTestCase):
    def setUp(self):
        super().setUp()
        self.app = CatApp(redis_url='15')
        self.app.r.flushdb()
        self.app.update()
        self.staff_member = self.app.login()
        self.user = self.app.login()

class ApplicationTest(MicroTestCase):
    def test_init_redis_url_invalid(self):
        with self.assertRaisesRegex(micro.ValueError, 'redis_url_invalid'):
            CatApp(redis_url='//localhost:foo')

    def test_authenticate(self):
        user = self.app.authenticate(self.user.auth_secret)
        self.assertEqual(user, self.user)
        self.assertEqual(user, self.app.user)

    def test_authenticate_secret_invalid(self):
        with self.assertRaises(micro.AuthenticationError):
            self.app.authenticate('foo')

    def test_login(self):
        # login() is called by setUp()
        self.assertIn(self.user.id, self.app.users)
        self.assertEqual(self.user, self.app.user)
        self.assertIn(self.staff_member, self.app.settings.staff)

    def test_login_no_redis(self):
        app = CatApp(redis_url='//localhost:16160')
        with self.assertRaises(RedisError):
            app.login()

    def test_login_code(self):
        user = self.app.login(code=self.staff_member.auth_secret)
        self.assertEqual(user, self.staff_member)

    def test_login_code_invalid(self):
        with self.assertRaisesRegex(micro.ValueError, 'code_invalid'):
            self.app.login(code='foo')

class ApplicationUpdateTest(AsyncTestCase):
    @staticmethod
    def setup_db(tag):
        d = mkdtemp()
        check_call(['git', '-c', 'advice.detachedHead=false', 'clone', '-q', '--single-branch',
                    '--branch', tag, '.', d])
        check_call(['python3', '-c', SETUP_DB_SCRIPT], cwd=d)

    def test_update_db_fresh(self):
        app = CatApp(redis_url='15')
        app.r.flushdb()
        app.update()
        self.assertEqual(app.settings.title, 'CatApp')

    def test_update_db_version_previous(self):
        self.setup_db('0.13.0')
        app = CatApp(redis_url='15')
        app.update()

        user = app.settings.staff[0]
        self.assertTrue(app.settings.push_vapid_private_key)
        self.assertTrue(app.settings.push_vapid_public_key)
        self.assertIsNotNone(app.activity.subscribers)
        self.assertEqual(user.device_notification_status, 'off')
        self.assertIsNone(user.push_subscription)

    def test_update_db_version_first(self):
        # NOTE: Tag tmp can be removed on next database update
        self.setup_db('tmp')
        app = CatApp(redis_url='15')
        app.update()

        # Update to version 3
        self.assertFalse(app.settings.provider_description)
        # Update to version 4
        self.assertNotIn('trashed', app.settings.json())
        self.assertFalse(app.r.oget('Cat').trashed)
        # Update to version 5
        self.assertFalse(hasattr(app.settings, 'favicon'))
        self.assertIsNone(app.settings.icon_small)
        self.assertIsNone(app.settings.icon_large)
        # Update to version 6
        user = app.settings.staff[0]
        self.assertTrue(app.settings.push_vapid_private_key)
        self.assertTrue(app.settings.push_vapid_public_key)
        self.assertIsNotNone(app.activity.subscribers)
        self.assertEqual(user.device_notification_status, 'off')
        self.assertIsNone(user.push_subscription)

class EditableTest(MicroTestCase):
    def setUp(self):
        super().setUp()
        self.cat = self.app.cats.create()

    def test_edit(self):
        self.cat.edit(name='Happy')
        self.cat.edit(name='Grumpy')
        user2 = self.app.login()
        self.cat.edit(name='Hover')
        self.assertEqual(self.cat.authors, [self.user, user2])

    def test_edit_cat_trashed(self):
        self.cat.trash()
        with self.assertRaisesRegex(micro.ValueError, 'object_trashed'):
            self.cat.edit(name='Happy')

    def test_edit_user_anonymous(self):
        self.app.user = None
        with self.assertRaises(micro.PermissionError):
            self.cat.edit(name='Happy')

class TrashableTest(MicroTestCase):
    def test_trash(self):
        cat = self.app.cats.create()
        cat.trash()
        self.assertTrue(cat.trashed)
        self.assertEqual(cat.activity[0].type, 'trashable-trash')

    def test_trash_trashed(self):
        cat = self.app.cats.create()
        cat.trash()
        cat.trash()
        self.assertTrue(cat.trashed)
        self.assertEqual(len(cat.activity), 1)

    def test_restore(self):
        cat = self.app.cats.create()
        cat.trash()
        cat.restore()
        self.assertFalse(cat.trashed)
        self.assertEqual(cat.activity[0].type, 'trashable-restore')

class OrderableTest(MicroTestCase):
    def make_cats(self):
        return [self.app.cats.create(), self.app.cats.create(), self.app.cats.create()]

    def make_external_cat(self):
        return Cat(id='Cat', app=self.app, authors=[], trashed=False, name=None,
                   activity=Activity('Cat.activity', self.app, subscriber_ids=[]))

    def test_move(self):
        cats = self.make_cats()
        self.app.cats.move(cats[1], cats[2])
        self.assertEqual(list(self.app.cats.values()), [cats[0], cats[2], cats[1]])

    def test_move_to_none(self):
        cats = self.make_cats()
        self.app.cats.move(cats[1], None)
        self.assertEqual(list(self.app.cats.values()), [cats[1], cats[0], cats[2]])

    def test_move_to_item(self):
        cats = self.make_cats()
        self.app.cats.move(cats[1], cats[1])
        self.assertEqual(list(self.app.cats.values()), cats)

    def test_move_item_external(self):
        cats = self.make_cats()
        external = self.make_external_cat()
        with self.assertRaisesRegex(micro.ValueError, 'item_not_found'):
            self.app.cats.move(external, cats[0])

    def test_move_to_external(self):
        cats = self.make_cats()
        external = self.make_external_cat()
        with self.assertRaisesRegex(micro.ValueError, 'to_not_found'):
            self.app.cats.move(cats[0], external)

class UserTest(MicroTestCase):
    def test_edit(self):
        self.user.edit(name='Happy')
        self.assertEqual(self.user.name, 'Happy')

class ActivityTest(MicroTestCase):
    def make_activity(self):
        return Activity('Activity:more', self.app, subscriber_ids=[])

    @patch('micro.User.notify', autospec=True)
    def test_publish(self, notify):
        activity = self.make_activity()
        activity.subscribe()
        self.app.login()
        activity.subscribe()

        event = Event.create('meow', None, app=self.app)
        activity.publish(event)
        self.assertIn(event, activity)
        notify.assert_called_once_with(self.user, event)

    def test_subscribe(self):
        activity = self.make_activity()
        activity.subscribe()
        self.assertIn(self.user, activity.subscribers)

    def test_unsubscribe(self):
        activity = self.make_activity()
        activity.subscribe()
        activity.unsubscribe()
        self.assertNotIn(self.user, activity.subscribers)

class LocationTest(MicroTestCase):
    def test_parse(self):
        location = Location.parse({'name': 'Berlin', 'coords': [52.504043, 13.393236]})
        self.assertEqual(location.name, 'Berlin')
        self.assertEqual(location.coords, (52.504043, 13.393236))
