User is editable by the user oneself.

.. include:: micro/object-attributes.inc

.. include:: micro/editable-attributes.inc

.. describe:: name

   Name or nick name.

.. describe:: email

   Email address, being a single line string. May be ``None``. Visible only to the user oneself.

.. describe:: create_time

   Time the user account was created. Visible only to the user oneself.

.. describe:: authenticate_time

   Time the user last authenticated. Visible only to the user oneself.

.. attribute:: devices

   Registered user :ref:`UserDevices`.
