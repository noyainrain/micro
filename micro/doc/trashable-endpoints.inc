.. http:post:: /api/(object-url)/trash

   Trash (delete) the object.

   If the object is already trashed, nothing happens.

   Permission: Authenticated users.

.. http:post:: /api/(object-url)/restore

   Restore the previously trashed (deleted) object.

   If the object is not trashed, nothing happens.

   Permission: Authenticated users.
