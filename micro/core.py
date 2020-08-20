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

"""Core parts of micro.

.. data: RewriteFunc

   Function of the form ``rewrite(url)`` which rewrites the given *url*.
"""

from contextvars import ContextVar
import typing
from typing import Callable, Optional

if typing.TYPE_CHECKING:
    from micro import User

RewriteFunc = Callable[[str], str]

class context:
    """Application context.

    .. attribute:: user

       Current user. Defaults to ``None``, meaning anonymous access.

    .. attribute:: client

       Identifier of the current client, e.g. a network address. Defaults to ``local``.
    """
    # pylint: disable=invalid-name; namespace

    user: ContextVar[Optional['User']] = ContextVar('user', default=None)
    client = ContextVar('client', default='local')
