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

"""micro errors."""

import builtins

class Error(Exception):
    """Base for micro errors."""
    pass

class ValueError(builtins.ValueError, Error):
    """See :ref:`ValueError`.

    The first item of *args* is also available as *code*.
    """

    @property
    def code(self):
        # pylint: disable=missing-docstring; already documented
        return self.args[0] if self.args else None

class CommunicationError(Error):
    """See :ref:`CommunicationError`."""
    pass
