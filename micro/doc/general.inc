Introduction
------------

The application provides a JSON REST API.

Arguments are passed to an endpoint simply as JSON object and the result is returned as JSON value.
*Objects* contain a ``__type__`` attribute that holds the name of the object type.

If a requested endpoint doesn't exist, a :ref:`NotFoundError` is returned. For any endpoint, an
:ref:`InputError` is returned if the input contains invalid arguments.

The URL that uniquely identifies an object is referred to as *object-url*, e.g. ``users/abc`` for a
:ref:`User` with the *id* ``abc``.

Authentication and Permissions
------------------------------

To make an API request authenticated as some user, include a cookie named ``auth_secret`` with the
:ref:`User` 's *auth_secret*.

If user authentication with the given secret fails, an :ref:`AuthenticationError` is returned. For
any endpoint, a :ref:`PermissionError` is returned if the current user is not allowed to perform the
action.

Additional types
----------------

A *slice* represents a range of a list, as array ``[start, stop]``, from index *start* (inclusive)
to *stop* (exclusive). Both *start* and *stop* may be ``null``, referring to the beginning (0) and
end (list length) of the list respectively.

A *slice string* has the form ``{start}:{stop}``. Both *start* and *stop* may be omitted, meaning
``null``.

A *polyglot string* is an :class:`Object` holding multiple translations of a string indexed by short
language tag.

Usage examples
--------------

A new :ref:`User` is created and logged in with the following request::

    $ curl -d "" https://example.org/api/login
    {
        "__type__": "User",
        "id": "abcd",
        "auth_secret": "wxyz",
        ...
    }

To authenticate further API calls, the returned *auth_secret* is set as cookie.

Setting a user's *email* address requires multiple steps. First::

    $ curl -b "auth_secret=wxyz" -d '{"email": "happy@example.org"}' \
           https://example.org/api/users/abcd/set-email
    {
        "__type__": "AuthRequest",
        "id": "efgh"
    }

This triggers a third party authentication via the email provider (as layed out in
:ref:`AuthRequest`). The resulting authentication code (here ``stuv``) is then verified to finish
setting the email address::

    $ curl -b "auth_secret=wxyz" -d '{"auth_request_id": "efgh", "auth": "stuv"}' \
           https://example.org/api/users/abcd/finish-set-email
    {
        "__type__": "User",
        "id": "abcd",
        "email": "happy@example.org",
        ...
    }

.. _Collection:

Collection
----------

Collection of objects.

.. include:: micro/collection-attributes.inc

.. include:: micro/collection-endpoints.inc

.. _AuthRequest:

AuthRequest
-----------

Third party authentication request.

To set an :ref:`User` 's email address, a third party authentication via the email provider is
performed to proof ownership over the address: First an email message containing a secret
authentication code is sent to the user. The email provider authenticates the user by login to their
mailbox, where they retrieve the code. Finally the code is passed back to and verified by the
application.

.. include:: micro/object-attributes.inc

.. _User:

User
----

User is editable by the user oneself.

.. include:: micro/object-attributes.inc

.. include:: micro/editable-attributes.inc

.. describe:: name

   Name or nick name.

.. describe:: email

   Email address, being a single line string. May be ``None``. Visible only to the user oneself.

.. describe:: auth_secret

   Secret for authentication. Visible only to the user oneself.

.. describe:: device_notification_status

   Device notification status:

   * ``on``: Notifications are enabled
   * ``off``: Notifications are disabled
   * ``off.expired``: Notifications are disabled because *push_subscription* expired

.. describe:: push_subscription

   Push subscription token used for sending device notifications. May be ``null``.

.. http:get:: /api/users/(id)

   Get the user given by *id*.

.. include:: micro/editable-endpoints.inc

.. http:post:: /api/users/(id)/set-email

   {"email"}

   Start to set the user's *email* address.

   A third party authentication via the email provider (as layed out in :ref:`AuthRequest`) is
   triggered and a corresponding :ref:`AuthRequest` is returned. To finish setting the email address
   use :http:post:`/api/users/(id)/finish-set-email`.

   Permission: The user oneself.

.. http:post:: /api/users/(id)/finish-set-email

   {"auth_request_id", "auth"}

   Finish setting the user's *email* address and return the user.

   *auth* is the authentication code, resulting from the :ref:`AuthRequest` with *auth_request_id*,
   to be verified. If the verification fails, a :ref:`ValueError` (``auth_invalid``) is returned. If
   the given email address is already associated with another user, a :ref:`ValueError`
   (``email_duplicate``) is returned.

   Permission: The user oneself.

.. http:post:: /api/users/(id)/remove-email

   Remove the user's current *email* address and return the user.

   If the user's *email* is not set, a :ref:`ValueError` (``user_no_email``) is returned.

   Permission: The user oneself.

.. http:patch:: /api/users/(id)

   ``{"op": "enable_device_notifications", "push_subscription"}``

   Enable device notifications, using *push_subscription*.

   A confirmation message is sent to the device. If there is a communication issue, a
   :ref:`CommunicationError` is returned.

   Permission: The user oneself.

   ``{"op": "disable_device_notifications"}``

   Disable device notifications.

   Permission: The user oneself.

.. _Activity:

Activity
--------

Activity feed (of events) around a common topic/context.

*activity-url* is the URL that identifies the activity feed, e.g. ``/api/activity``.

.. describe:: user_subscribed

   Indicates if the user subscribed to the feed.

.. describe:: items

   List of recorded :ref:`Event` s.

.. http:patch:: /api/(activity-url)

   ``{"op": "subscribe"}``

   Subscribe the user to the feed.

   Permission: Authenticated users.

   ``{"op": "unsubscribe"}``

   Unsubscribe the user from the feed.

   Permission: Authenticated users.

.. http:get:: /api/(activity-url)/stream

   Get a live stream of :ref:`Event`s as ``text/event-stream``.

.. _Event:

Event
-----

Event about an action on an *object* by an *user*.

.. include:: micro/object-attributes.inc

.. attribute:: type

   Type of the event.

.. attribute:: object

   Object for which the event happened. ``null`` if it is a global event.

.. attribute:: user

   :ref:`User` who triggered the event.

.. describe:: time

   Date and time at which the event happened.

.. attribute:: detail

   Dictionary with additonal details about the event. The contents depend on the event *type*.

.. _Location:

Location
--------

Location.

.. describe:: name

   Name of the location.

.. describe:: coords

   Coordinates as latitude-longitude pair. May be ``null``.

.. _Resource:

Resource
--------

Web resource description.

.. include:: micro/resource-attributes.inc

.. _Image:

Image
-----

Image :ref:`Resource` description.

Note that the *image* representation is always ``null``.

.. include:: micro/resource-attributes.inc

.. _Video:

Video
-----

Video :ref:`Resource` description.

.. include:: micro/resource-attributes.inc

Errors
------

.. _ValueError:

ValueError
^^^^^^^^^^

Returned for value-related errors.

.. attribute:: code

   Error string providing more information about the problem.

   .. deprecated:: 0.27.0

      Use :attr:`message` instead.

.. _InputError:

InputError
^^^^^^^^^^

Returned if the input to an endpoint contains one or more arguments with an invalid value.

InputError is a :ref:`ValueError` with *code* set to ``input_invalid``.

.. attribute:: errors

   Map of argument names / error strings for every problematic argument of the input.

.. _NotFoundError:

NotFoundError
^^^^^^^^^^^^^

Returned if a requested endpoint does not exist.

.. _AuthenticationError:

AuthenticationError
^^^^^^^^^^^^^^^^^^^

Returned if user authentication fails.

.. _PermissionError:

PermissionError
^^^^^^^^^^^^^^^

Returned if the current user is not allowed to perform an action.

.. _CommunicationError:

CommunicationError
^^^^^^^^^^^^^^^^^^

Returned if communication with a third party fails.

.. _AnalysisError:

AnalysisError
^^^^^^^^^^^^^

Returned if analyzing a web resource fails.

.. _NoResourceError:

NoResourceError
^^^^^^^^^^^^^^^

:ref:`AnalysisError` returned if there is no resource at the URL to analyze.

.. _ForbiddenResourceError:

ForbiddenResourceError
^^^^^^^^^^^^^^^^^^^^^^

:ref:`AnalysisError` returned if access to the resource subject to analysis is forbidden.

.. _BorkenResourceError:

BrokenResourceError
^^^^^^^^^^^^^^^^^^^

:ref:`AnalysisError` returned if the resource subject to analysis is broken.
