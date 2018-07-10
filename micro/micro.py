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

"""Core parts of micro."""

import builtins
from collections.abc import Mapping
from datetime import datetime
from email.message import EmailMessage
import errno
import json
from logging import getLogger
import os
import re
from smtplib import SMTP
from typing import ( # pylint: disable=unused-import; type checking
    Callable, Dict, List, Optional, Type, Union, cast)
from urllib.parse import urlparse

from pywebpush import WebPusher, WebPushException
from py_vapid import Vapid
from py_vapid.utils import b64urlencode
from redis import StrictRedis
from redis.exceptions import ResponseError
from tornado.httpclient import AsyncHTTPClient, HTTPError
from tornado.ioloop import IOLoop
from typing_extensions import Protocol

from micro.jsonredis import JSONRedis, JSONRedisSequence, JSONRedisMapping, expect_type
from .util import check_email, randstr, parse_isotime, str_or_none, version

_PUSH_TTL = 24 * 60 * 60

class JSONifiable(Protocol):
    """TODO."""
    def __init__(self, **kwargs: object) -> None:
        # pylint: disable=super-init-not-called; protocol
        pass

    def json(self, restricted: bool = False, include: bool = False) -> Dict[str, object]:
        """TODO."""
        pass

class Application:
    """Social micro web app.

    .. attribute:: user

       Current :class:`User`. ``None`` means anonymous access.

    .. attribute:: users

       Map of all :class:`User` s.

    .. attribute:: redis_url

       See ``--redis-url`` command line option.

    .. attribute:: email

       Sender email address to use for outgoing email. Defaults to ``bot@localhost``.

    .. attribute:: smtp_url

       See ``--smtp-url`` command line option.

    .. attribute:: render_email_auth_message

       Hook function of the form *render_email_auth_message(email, auth_request, auth)*, responsible
       for rendering an email message for the authentication request *auth_request*. *email* is the
       email address to authenticate and *auth* is the secret authentication code.

    .. attribute:: r

       :class:`Redis` database. More precisely a :class:`JSONRedis` instance.
    """

    def __init__(
            self, redis_url: str = '', email: str = 'bot@localhost', smtp_url: str = '',
            render_email_auth_message: 'Callable[[str, AuthRequest, str], str]' = None) -> None:
        check_email(email)
        try:
            # pylint: disable=pointless-statement; port errors are only triggered on access
            urlparse(smtp_url).port
        except builtins.ValueError:
            raise ValueError('smtp_url_invalid')

        self.redis_url = redis_url
        try:
            self.r = JSONRedis(StrictRedis.from_url(self.redis_url), self._encode, self._decode)
        except builtins.ValueError:
            raise ValueError('redis_url_invalid')

        self.types = {
            'User': User,
            'Settings': Settings,
            'Activity': Activity,
            'Event': Event,
            'AuthRequest': AuthRequest
        } # type: Dict[str, Type[JSONifiable]]
        self.user = None
        self.users = JSONRedisMapping(self.r, 'users', expect_type(User))
        self.email = email
        self.smtp_url = smtp_url
        self.render_email_auth_message = render_email_auth_message

    @property
    def settings(self):
        """App :class:`Settings`."""
        return self.r.oget('Settings')

    @property
    def activity(self) -> 'Activity':
        """Global :class:`Activity` feed."""
        activity = self.r.oget('Activity', default=KeyError, expect=expect_type(Activity))
        activity.pre = self.check_user_is_staff
        return activity

    def update(self):
        """Update the database.

        If the database is fresh, it will be initialized. If the database is already up-to-date,
        nothing will be done. It is thus safe to call :meth:`update` without knowing if an update is
        necessary or not.
        """
        v = self.r.get('micro_version')

        # If fresh, initialize database
        if not v:
            settings = self.create_settings()
            settings.push_vapid_private_key, settings.push_vapid_public_key = (
                self._generate_push_vapid_keys())
            self.r.oset(settings.id, settings)
            activity = Activity(id='Activity', app=self, subscriber_ids=[])
            self.r.oset(activity.id, activity)
            self.r.set('micro_version', 6)
            self.do_update()
            return

        v = int(v)
        r = JSONRedis(self.r.r)
        r.caching = False

        # Deprecated since 0.15.0
        if v < 3:
            settings = r.oget('Settings')
            settings['provider_name'] = None
            settings['provider_url'] = None
            settings['provider_description'] = {}
            r.oset(settings['id'], settings)
            r.set('micro_version', 3)

        # Deprecated since 0.6.0
        if v < 4:
            for obj in self._scan_objects(r):
                if not issubclass(self.types[obj['__type__']], Trashable):
                    del obj['trashed']
                    r.oset(obj['id'], obj)
            r.set('micro_version', 4)

        # Deprecated since 0.13.0
        if v < 5:
            settings = r.oget('Settings')
            settings['icon_small'] = settings['favicon']
            del settings['favicon']
            settings['icon_large'] = None
            r.oset(settings['id'], settings)
            r.set('micro_version', 5)

        # Deprecated since 0.14.0
        if v < 6:
            settings = r.oget('Settings')
            settings['push_vapid_private_key'], settings['push_vapid_public_key'] = (
                self._generate_push_vapid_keys())
            r.oset(settings['id'], settings)
            activity = Activity(id='Activity', app=self, subscriber_ids=[]).json()
            r.oset(activity['id'], activity)

            users = r.omget(r.lrange('users', 0, -1))
            for user in users:
                user['device_notification_status'] = 'off'
                user['push_subscription'] = None
            r.omset({user['id']: user for user in users})
            r.set('micro_version', 6)

        self.do_update()

    def do_update(self):
        """Subclass API: Perform the database update.

        May be overridden by subclass. Called by :meth:`update`, which takes care of updating (or
        initializing) micro specific data. The default implementation does nothing.
        """
        pass

    def create_settings(self):
        """Subclass API: Create and return the app :class:`Settings`.

        *id* must be set to ``Settings``.

        Must be overridden by subclass. Called by :meth:`update` when initializing the database.
        """
        raise NotImplementedError()

    def authenticate(self, secret):
        """Authenticate an :class:`User` (device) with *secret*.

        The identified user is set as current *user* and returned. If the authentication fails, an
        :exc:`AuthenticationError` is raised.
        """
        id = self.r.hget('auth_secret_map', secret)
        if not id:
            raise AuthenticationError()
        self.user = self.users[id.decode()]
        return self.user

    def login(self, code=None):
        """See :http:post:`/api/login`.

        The logged-in user is set as current *user*.
        """
        if code:
            id = self.r.hget('auth_secret_map', code)
            if not id:
                raise ValueError('code_invalid')
            user = self.users[id.decode()]

        else:
            id = 'User:' + randstr()
            user = User(
                id=id, app=self, authors=[id], name='Guest', email=None, auth_secret=randstr(),
                device_notification_status='off', push_subscription=None)
            self.r.oset(user.id, user)
            self.r.rpush('users', user.id)
            self.r.hset('auth_secret_map', user.auth_secret, user.id)

            # Promote first user to staff
            if len(self.users) == 1:
                settings = self.settings
                # pylint: disable=protected-access; Settings is a friend
                settings._staff = [user.id]
                self.r.oset(settings.id, settings)

        return self.authenticate(user.auth_secret)

    def get_object(self, id, default=KeyError):
        """Get the :class:`Object` given by *id*.

        *default* is the value to return if no object with *id* is found. If it is an
        :exc:`Exception`, it is raised instead.
        """
        object = self.r.oget(id)
        if object is None:
            object = default
        if isinstance(object, Exception):
            raise object
        return object

    def check_user_is_staff(self) -> None:
        """Check if the current :attr:`user` is a staff member."""
        # pylint: disable=protected-access; Settings is a friend
        if not (self.user and self.user.id in self.settings._staff):
            raise PermissionError()

    @staticmethod
    def _encode(object: JSONifiable) -> Dict[str, object]:
        try:
            return object.json()
        except AttributeError:
            raise TypeError()

    def _decode(self, json: Dict[str, object]) -> Union[JSONifiable, Dict[str, object]]:
        # pylint: disable=redefined-outer-name; good name
        try:
            type_name = json.pop('__type__')
        except KeyError:
            return json
        if not isinstance(type_name, str):
            return json
        type = self.types[type_name]
        # Compatibility for Settings without icon_large (deprecated since 0.13.0)
        if issubclass(type, Settings):
            json['v'] = 2
        return type(app=self, **json)

    @staticmethod
    def _scan_objects(r):
        for key in r.keys('*'):
            try:
                obj = r.oget(key)
            except ResponseError:
                pass
            else:
                if isinstance(obj, Mapping) and '__type__' in obj:
                    yield obj

    @staticmethod
    def _generate_push_vapid_keys():
        vapid = Vapid()
        vapid.generate_keys()
        return (b64urlencode(vapid.private_key.private_numbers().private_value.to_bytes(32, 'big')),
                b64urlencode(vapid.public_key.public_numbers().encode_point()))

class Object:
    """Object in the application universe.

    .. attribute:: app

       Context :class:`Application`.
    """

    def __init__(self, id: str, app: Application) -> None:
        self.id = id
        self.app = app

    def json(self, restricted: bool = False, include: bool = False) -> Dict[str, object]:
        """Return a JSON object representation of the object.

        The name of the object type is included as ``__type__``.

        By default, all attributes are included. If *restricted* is ``True``, a restricted view of
        the object is returned, i.e. attributes that should not be available to the current
        :attr:`Application.user` are excluded. If *include* is ``True``, additional fields that may
        be of interest to the caller are included.

        Subclass API: May be overridden by subclass. The default implementation returns the
        attributes of :class:`Object`. *restricted* and *include* are ignored.
        """
        # pylint: disable=unused-argument; part of subclass API
        # Compatibility for trashed (deprecated since 0.6.0)
        return {
            '__type__': type(self).__name__,
            'id': self.id,
            **({'trashed': False} if restricted else {})
        }

    def __repr__(self):
        return '<{}>'.format(self.id)

class Editable:
    """:class:`Object` that can be edited."""
    # pylint: disable=no-member; mixin
    app = None # type: Application

    def __init__(self, authors: List[str], activity: 'Activity' = None) -> None:
        self._authors = authors
        self.__activity = activity

    @property
    def authors(self) -> List['User']:
        # pylint: disable=missing-docstring; already documented
        authors = self.app.r.omget(self._authors)
        assert all(isinstance(author, User) for author in authors)
        return cast(List[User], authors)

    def edit(self, **attrs):
        """See :http:post:`/api/(object-url)`."""
        if not self.app.user:
            raise PermissionError()
        if isinstance(self, Trashable) and self.trashed:
            raise ValueError('object_trashed')

        self.do_edit(**attrs)
        if not self.app.user.id in self._authors:
            self._authors.append(self.app.user.id)
        self.app.r.oset(self.id, self)

        if self.__activity is not None:
            activity = self.__activity() if callable(self.__activity) else self.__activity
            activity.publish(Event.create('editable-edit', self, app=self.app))

    def do_edit(self, **attrs):
        """Subclass API: Perform the edit operation.

        More precisely, validate and then set the given *attrs*.

        Must be overridden by host. Called by :meth:`edit`, which takes care of basic permission
        checking, managing *authors* and storing the updated object in the database.
        """
        raise NotImplementedError()

    def json(self, restricted: bool = False, include: bool = False) -> Dict[str, object]:
        """Subclass API: Return a JSON object representation of the editable part of the object."""
        return {'authors': [a.json(restricted) for a in self.authors] if include else self._authors}

class Trashable:
    """Mixin for :class:`Object` which can be trashed and restored."""
    # pylint: disable=no-member; mixin

    def __init__(self, trashed, activity=None):
        self.trashed = trashed
        self.__activity = activity

    def trash(self):
        """See :http:post:`/api/(object-url)/trash`."""
        if not self.app.user:
            raise PermissionError()
        if self.trashed:
            return

        self.trashed = True
        self.app.r.oset(self.id, self)
        if self.__activity is not None:
            activity = self.__activity() if callable(self.__activity) else self.__activity
            activity.publish(Event.create('trashable-trash', self, app=self.app))

    def restore(self):
        """See :http:post:`/api/(object-url)/restore`."""
        if not self.app.user:
            raise PermissionError()
        if not self.trashed:
            return

        self.trashed = False
        self.app.r.oset(self.id, self)
        if self.__activity is not None:
            activity = self.__activity() if callable(self.__activity) else self.__activity
            activity.publish(Event.create('trashable-restore', self, app=self.app))

    def json(self, restricted=False, include=False):
        """Subclass API: Return a JSON representation of the trashable part of the object."""
        # pylint: disable=unused-argument; part of subclass API
        return {'trashed': self.trashed}

class Collection(JSONRedisMapping):
    """Collection of :class:`Object` s.

    .. attribute:: host

       Tuple ``(object, attr)`` that specifies the attribute name *attr* on the host *object*
       (:class:`Object` or :class:`Application`) the collection is attached to.

    .. attribute:: app

       Context :class:`Application`.
    """

    def __init__(self, host):
        self.host = host
        self.app = host[0] if isinstance(host[0], Application) else host[0].app
        super().__init__(
            self.app.r,
            ('' if isinstance(host[0], Application) else host[0].id + '.') + self.host[1])

class Orderable:
    """Mixin for :class:`Collection` whose items can be ordered."""
    # pylint: disable=no-member; mixin
    # pylint: disable=unsupported-membership-test; mixin

    def move(self, item, to):
        """See :http:post:`/api/(collection-path)/move`."""
        if to:
            if to.id not in self:
                raise ValueError('to_not_found')
            if to == item:
                # No op
                return
        if not self.r.lrem(self.map_key, 1, item.id):
            raise ValueError('item_not_found')
        if to:
            self.r.linsert(self.map_key, 'after', to.id, item.id)
        else:
            self.r.lpush(self.map_key, item.id)

class User(Object, Editable):
    """See :ref:`User`."""

    def __init__(
            self, id: str, app: Application, authors: List[str], name: str, email: str,
            auth_secret: str, device_notification_status: str,
            push_subscription: Optional[str]) -> None:
        super().__init__(id, app)
        Editable.__init__(self, authors=authors)
        self.name = name
        self.email = email
        self.auth_secret = auth_secret
        self.device_notification_status = device_notification_status
        self.push_subscription = push_subscription

    def store_email(self, email):
        """Update the user's *email* address.

        If *email* is already associated with another user, a :exc:`ValueError`
        (``email_duplicate``) is raised.
        """
        check_email(email)
        id = self.app.r.hget('user_email_map', email)
        if id and id.decode() != self.id:
            raise ValueError('email_duplicate')

        if self.email:
            self.app.r.hdel('user_email_map', self.email)
        self.email = email
        self.app.r.oset(self.id, self)
        self.app.r.hset('user_email_map', self.email, self.id)

    def set_email(self, email):
        """See :http:post:`/api/users/(id)/set-email`."""
        if self.app.user != self:
            raise PermissionError()
        check_email(email)

        code = randstr()
        auth_request = AuthRequest(id='AuthRequest:' + randstr(), app=self.app, email=email,
                                   code=code)
        self.app.r.oset(auth_request.id, auth_request)
        self.app.r.expire(auth_request.id, 10 * 60)
        if self.app.render_email_auth_message:
            self._send_email(email, self.app.render_email_auth_message(email, auth_request, code))
        return auth_request

    def finish_set_email(self, auth_request, auth):
        """See :http:post:`/api/users/(id)/finish-set-email`."""
        # pylint: disable=protected-access; auth_request is a friend
        if self.app.user != self:
            raise PermissionError()
        if auth != auth_request._code:
            raise ValueError('auth_invalid')

        self.app.r.delete(auth_request.id)
        self.store_email(auth_request._email)

    def remove_email(self):
        """See :http:post:`/api/users/(id)/remove-email`."""
        if self.app.user != self:
            raise PermissionError()
        if not self.email:
            raise ValueError('user_no_email')

        self.app.r.hdel('user_email_map', self.email)
        self.email = None
        self.app.r.oset(self.id, self)

    def send_email(self, msg):
        """Send an email message to the user.

        *msg* is the message string of the following form: It starts with a line containing the
        subject prefixed with ``Subject:_``, followed by a blank line, followed by the body.

        If the user's ::attr:`email` is not set, a :exc:`ValueError` (``user_no_email``) is raised.
        If communication with the SMTP server fails, an :class:`EmailError` is raised.
        """
        if not self.email:
            raise ValueError('user_no_email')
        self._send_email(self.email, msg)

    def notify(self, event):
        """Notify the user about the :class:`Event` *event*.

        If :attr:`push_subscription` has expired, device notifications are disabled.
        """
        if self.device_notification_status != 'on':
            return
        IOLoop.current().add_callback(self._notify, event)

    async def enable_device_notifications(self, push_subscription):
        """See :http:patch:`/api/users/(id)` (``enable_device_notifications``)."""
        if self.app.user != self:
            raise PermissionError()
        await self._send_device_notification(
            push_subscription, Event.create('user-enable-device-notifications', self, app=self.app))
        self.device_notification_status = 'on'
        self.push_subscription = push_subscription
        self.app.r.oset(self.id, self)

    def disable_device_notifications(self, user: Optional['User']) -> None:
        """See :http:patch:`/api/users/(id)` (``disable_device_notifications``)."""
        if user != self:
            raise PermissionError()
        self._disable_device_notifications()

    def _disable_device_notifications(self, reason: str = None) -> None:
        self.device_notification_status = 'off.{}'.format(reason) if reason else 'off'
        self.push_subscription = None
        self.app.r.oset(self.id, self)

    def do_edit(self, **attrs):
        if self.app.user != self:
            raise PermissionError()

        e = InputError()
        if 'name' in attrs and not str_or_none(attrs['name']):
            e.errors['name'] = 'empty'
        e.trigger()

        if 'name' in attrs:
            self.name = attrs['name']

    def json(self, restricted: bool = False, include: bool = False) -> Dict[str, object]:
        """See :meth:`Object.json`."""
        return {
            **super().json(restricted, include),
            **Editable.json(self, restricted, include),
            'name': self.name,
            **(
                {} if restricted and self.app.user != self else {
                    'email': self.email,
                    'auth_secret': self.auth_secret,
                    'device_notification_status': self.device_notification_status,
                    'push_subscription': self.push_subscription
                })
        }

    def _send_email(self, to, msg):
        match = re.fullmatch(r'Subject: ([^\n]+)\n\n(.+)', msg, re.DOTALL)
        if not match:
            raise ValueError('msg_invalid')

        msg = EmailMessage()
        msg['To'] = to
        msg['From'] = self.app.email
        msg['Subject'] = match.group(1)
        msg.set_content(match.group(2))

        components = urlparse(self.app.smtp_url)
        host = components.hostname or 'localhost'
        port = components.port or 25
        try:
            with SMTP(host=host, port=port) as smtp:
                smtp.send_message(msg)
        except OSError:
            raise EmailError()

    async def _notify(self, event):
        try:
            await self._send_device_notification(self.push_subscription, event)
        except (ValueError, CommunicationError) as e:
            if isinstance(e, ValueError):
                if e.code != 'push_subscription_invalid':
                    raise e
                self._disable_device_notifications(reason='expired')
            getLogger(__name__).error('Failed to deliver notification: %s', str(e))

    async def _send_device_notification(self, push_subscription, event):
        try:
            push_subscription = json.loads(push_subscription)
            if not isinstance(push_subscription, dict):
                raise builtins.ValueError()
            urlparts = urlparse(push_subscription.get('endpoint'))
            pusher = WebPusher(push_subscription, self._HTTPClient)
        except (builtins.ValueError, WebPushException):
            raise ValueError('push_subscription_invalid')

        # Unfortunately sign() tries to validate the email address
        email = 'bot@email.localhost' if self.app.email == 'bot@localhost' else self.app.email
        headers = Vapid.from_raw(self.app.settings.push_vapid_private_key.encode()).sign({
            'aud': '{}://{}'.format(urlparts.scheme, urlparts.netloc),
            'sub': 'mailto:{}'.format(email)
        })

        try:
            response = await pusher.send(json.dumps(event.json(restricted=True, include=True)),
                                         headers, ttl=_PUSH_TTL)
        except OSError as e:
            raise CommunicationError(str(e))
        if response.code in (404, 410):
            raise ValueError('push_subscription_invalid')
        if response.code != 201:
            raise CommunicationError('Server responded with status {}'.format(response.code))

    class _HTTPClient:
        @staticmethod
        async def post(endpoint, data, headers, timeout):
            # pylint: disable=unused-argument, missing-docstring; part of API
            response = await AsyncHTTPClient().fetch(endpoint, method='POST', headers=headers,
                                                     body=data, raise_error=False)
            if response.code == 599:
                # Timeouts are given as HTTPError
                if isinstance(response.error, HTTPError):
                    raise TimeoutError(errno.ETIMEDOUT, os.strerror(errno.ETIMEDOUT))
                raise response.error
            return response

class Settings(Object, Editable):
    """See :ref:`Settings`.

    .. attribute:: push_vapid_private_key

       VAPID private key used for sending device notifications.
    """

    @version(1)
    def __init__(
            self, id, app, authors, title, icon, favicon, provider_name, provider_url,
            provider_description, feedback_url, staff):
        # pylint: disable=non-parent-init-called, super-init-not-called; versioned
        icon_small, icon_large = favicon, None
        self.__init__(id, app, authors, title, icon, icon_small, icon_large, provider_name,
                      provider_url, provider_description, feedback_url, staff, v=2)

    @__init__.version(2) # type: ignore
    def __init__(
            self, id, app, authors, title, icon, icon_small, icon_large, provider_name,
            provider_url, provider_description, feedback_url, staff, push_vapid_private_key=None,
            push_vapid_public_key=None):
        # pylint: disable=function-redefined; decorated
        # Compatibility for Settings without VAPID keys (deprecated since 0.14.0)
        super().__init__(id, app)
        Editable.__init__(self, authors=authors, activity=lambda: app.activity)
        self.title = title
        self.icon = icon
        self.icon_small = icon_small
        self.icon_large = icon_large
        self.provider_name = provider_name
        self.provider_url = provider_url
        self.provider_description = provider_description
        self.feedback_url = feedback_url
        self._staff = staff
        self.push_vapid_private_key = push_vapid_private_key
        self.push_vapid_public_key = push_vapid_public_key

    @property
    def staff(self):
        # pylint: disable=missing-docstring; already documented
        return self.app.r.omget(self._staff)

    def do_edit(self, **attrs):
        if not self.app.user.id in self._staff:
            raise PermissionError()

        # Compatibility for favicon (deprecated since 0.13.0)
        if 'favicon' in attrs:
            attrs.setdefault('icon_small', attrs['favicon'])

        e = InputError()
        if 'title' in attrs and not str_or_none(attrs['title']):
            e.errors['title'] = 'empty'
        e.trigger()

        if 'title' in attrs:
            self.title = attrs['title']
        if 'icon' in attrs:
            self.icon = str_or_none(attrs['icon'])
        if 'icon_small' in attrs:
            self.icon_small = str_or_none(attrs['icon_small'])
        if 'icon_large' in attrs:
            self.icon_large = str_or_none(attrs['icon_large'])
        if 'provider_name' in attrs:
            self.provider_name = str_or_none(attrs['provider_name'])
        if 'provider_url' in attrs:
            self.provider_url = str_or_none(attrs['provider_url'])
        if 'provider_description' in attrs:
            self.provider_description = attrs['provider_description']
        if 'feedback_url' in attrs:
            self.feedback_url = str_or_none(attrs['feedback_url'])

    def json(self, restricted=False, include=False):
        return {
            **super().json(restricted, include),
            **Editable.json(self, restricted, include),
            'title': self.title,
            'icon': self.icon,
            'icon_small': self.icon_small,
            'icon_large': self.icon_large,
            'provider_name': self.provider_name,
            'provider_url': self.provider_url,
            'provider_description': self.provider_description,
            'feedback_url': self.feedback_url,
            'staff': [u.json(restricted) for u in self.staff] if include else self._staff,
            'push_vapid_public_key': self.push_vapid_public_key,
            # Compatibility for favicon (deprecated since 0.13.0)
            **({'favicon': self.icon_small} if restricted else
               {'push_vapid_private_key': self.push_vapid_private_key})
        }

class Activity(Object, JSONRedisSequence['Event', JSONifiable]):
    """See :ref:`Activity`."""

    def __init__(self, id: str, app: Application, subscriber_ids: List[str],
                 pre: Callable[[], None] = None) -> None:
        super().__init__(id, app)
        JSONRedisSequence.__init__(self, app.r, '{}.items'.format(id), pre, expect_type(Event))
        self.host = None
        self._subscriber_ids = subscriber_ids
        self._live_subscribers = [] # type: List[Callable[[Event], None]]

    @property
    def subscribers(self) -> List[User]:
        """List of :class:`User`s who subscribed to the activity."""
        return self.app.r.omget(self._subscriber_ids, default=KeyError, expect=expect_type(User))

    def publish(self, event: 'Event') -> None:
        """Publish an *event* to the feed.

        All :attr:`subscribers`, except the user who triggered the event, are notified.
        """
        # If the event is published to multiple activity feeds, it is stored (and overwritten)
        # multiple times, but that's acceptable for a more convenient API
        print('publish', self, self._live_subscribers)
        self.r.oset(event.id, event)
        self.r.lpush(self.list_key, event.id)
        for subscriber in self.subscribers:
            if subscriber is not event.user:
                subscriber.notify(event) # type: ignore
        for notify in self._live_subscribers:
            notify(event)

    def subscribe(self):
        """See :http:patch:`/api/(activity-url)` (``subscribe``)."""
        if not self.app.user:
            raise PermissionError()
        if not self.app.user.id in self._subscriber_ids:
            self._subscriber_ids.append(self.app.user.id)
        self.app.r.oset(self.host.id if self.host else self.id, self.host or self)

    def unsubscribe(self):
        """See :http:patch:`/api/(activity-url)` (``unsubscribe``)."""
        if not self.app.user:
            raise PermissionError()
        try:
            self._subscriber_ids.remove(self.app.user.id)
        except ValueError:
            pass
        self.app.r.oset(self.host.id if self.host else self.id, self.host or self)

    def subscribe_live(self, notify: Callable[['Event'], None]) -> None:
        self._live_subscribers.append(notify)
        print('subscribe', self, self._live_subscribers)

    def json(self, restricted=False, include=False, slice=None):
        # pylint: disable=arguments-differ; extension
        return {
            **super().json(restricted, include),
            **({'user_subscribed': self.app.user.id in self._subscriber_ids} if restricted else
               {'subscriber_ids': self._subscriber_ids}),
            **({'items': event.json(True, True) for event in self[slice]} if slice else {})
        }

class Event(Object):
    """See :ref:`Event`."""

    @staticmethod
    def create(type, object, detail={}, app=None):
        """Create an event."""
        if not app.user:
            raise PermissionError()
        if not str_or_none(type):
            raise ValueError('type_empty')
        if any(k.endswith('_id') for k in detail):
            raise ValueError('detail_invalid_key')

        transformed = {}
        for key, value in detail.items():
            if isinstance(value, Object):
                key = key + '_id'
                value = value.id
            transformed[key] = value
        return Event(
            id='Event:' + randstr(), type=type, object=object.id if object else None,
            user=app.user.id, time=datetime.utcnow().isoformat() + 'Z', detail=transformed, app=app)

    def __init__(self, id: str, type: str, object: str, user: str, time: str,
                 detail: Dict[str, object], app: Application) -> None:
        super().__init__(id, app)
        self.type = type
        self.time = parse_isotime(time) if time else None
        self._object_id = object
        self._user_id = user
        self._detail = detail

    @property
    def object(self) -> Optional[Object]:
        # pylint: disable=missing-docstring; already documented
        return (self.app.r.oget(self._object_id, default=KeyError, expect=expect_type(Object))
                if self._object_id else None)

    @property
    def user(self) -> User:
        # pylint: disable=missing-docstring; already documented
        return self.app.users[self._user_id]

    @property
    def detail(self) -> Dict[str, '__builtins__.object']:
        # pylint: disable=missing-docstring; already documented
        detail = {}
        for key, value in self._detail.items():
            if key.endswith('_id'):
                key = key[:-3]
                assert isinstance(value, str)
                value = self.app.r.oget(value, default=ReferenceError)
            detail[key] = value
        return detail

    def json(self, restricted: bool = False,
             include: bool = False) -> Dict[str, '__builtins__.object']:
        # pylint: disable=redefined-outer-name; good name
        return {
            **super().json(restricted, include),
            'type': self.type,
            'time': self.time.isoformat() + 'Z' if self.time else None,
            **({
                'object': self.object.json(restricted) if self.object else None,
                'user': self.user.json(restricted),
                'detail': {k: v.json(restricted) if isinstance(v, Object) else v
                           for k, v in self.detail.items()}
            } if include else {
                'object': self._object_id,
                'user': self._user_id,
                'detail': self._detail
            })
        }

    def __str__(self) -> str:
        return '<{} {} on {} by {}>'.format(type(self).__name__, self.type, self._object_id,
                                            self._user_id)
    __repr__ = __str__

class AuthRequest(Object):
    """See :ref:`AuthRequest`."""

    def __init__(self, id: str, app: Application, email: str, code: str) -> None:
        super().__init__(id, app)
        self._email = email
        self._code = code

    def json(self, restricted=False, include=False):
        return {
            **super().json(restricted, include),
            **({} if restricted else {'email': self._email, 'code': self._code})
        }

class ValueError(builtins.ValueError):
    """See :ref:`ValueError`.

    The first item of *args* is also available as *code*.
    """

    @property
    def code(self):
        # pylint: disable=missing-docstring; already documented
        return self.args[0] if self.args else None

class InputError(ValueError):
    """See :ref:`InputError`.

    To raise an :exc:`InputError`, apply the following pattern::

       def meow(volume):
           e = InputError()
           if not 0 < volume <= 1:
               e.errors['volume'] = 'out_of_range'
           e.trigger()
           # ...
    """

    def __init__(self, errors={}):
        super().__init__('input_invalid')
        self.errors = dict(errors)

    def trigger(self):
        """Trigger the error, i.e. raise it if any *errors* are present.

        If *errors* is empty, do nothing.
        """
        if self.errors:
            raise self

class AuthenticationError(Exception):
    """See :ref:`AuthenticationError`."""
    pass

class PermissionError(Exception):
    """See :ref:`PermissionError`."""
    pass

class CommunicationError(Exception):
    """See :ref:`CommunicationError`."""
    pass

class EmailError(Exception):
    """Raised if communication with the SMTP server fails."""
    pass
