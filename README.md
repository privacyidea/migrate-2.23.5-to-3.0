# migrate-2.23.5-to-3.0

Tools to offline migrate privacyIDEA 2.23.5 to privacyIDEA 3.0

see https://github.com/privacyidea/privacyidea/issues/2040

In contrast to privacyIDEA 2.23.5 privacyIDEA 3.0 now stores the user assignments
in the database table "tokenowner" which will give us a greater flexibility in
future to assign tokens to users.

The following table explains the change of token assignment:

| table ``tokenowner`` in 3.0 | Corresponding database field in 2.23 | Comment |
| --------------------------- | ------------------------------------ | ------- |
| ``tokenowner.id`` |  | primary key, auto increment |
| ``tokenowner.token_id`` |  ``token.id`` | The reference to the ``token`` table |
| ``tokenowner.resolver`` | ``token.resolver`` |  |
| ``tokenowner.user_id`` | ``token.user_id`` |  |
| ``tokenowner.realm_id`` | ``tokenrealm.realm_id`` | We take the Corresponding value from the table ``tokenrealm`` |

So the database columns ``token.resolver`` and ``token.user_id`` are migrated
and the column ``token.resolver_type`` is not used anymore.

The original database migration script privacyidea/migrations/versions/48ee74b8a7c8_.py,
that is shipped with the privacyIDEA 3.x code, takes care of creating
the new table and migrating the data.

The postinst script of the install packages are running this migration scripts in
the packages postinst scripts.

However, due to additional business logic in the migration script, this takes a few
minutes per 1000 users. **Thus upgrading privacyIDEA with tens of thousands of
assigned tokens with this normal upgrade/migration script can take up to several
hours!**.

The tools in this very repository are ment to prepare the database schema and
the data in the database so that the update of privacyIDEA can run without
interupting normal operations for hours.

Now, the migrations would be done in several steps:

## Step 1: Update Schema

In the first step the normal DB migration is used with slitghtly modified
updates scripts.

**Be sure to specify the correct sub directory from this repository!**

    pi-manage db upgrade -d migrations-to-3/

This updates the database from alembic version ``1a0710df148b`` to
alembic version ``849170064430`` but without actually migrating the data and
without **dropping** the token assignment columns
from the token table - which would be done in a normal update.

This way the old code (2.23.5) can still run with this database.

At this point no data has been migrated. Nothing has changed, we only added
a database table and some columns.

However, the database schema version is already set to ``849170064430`` which
sould be reflected in the database table ``alembic_version``. This is the schema
version of privacyIDEA 3.0 with the migrated token assignments.

You are still running privacyIDEA 2.23.5!

## Step 2: Migrating the data

In this step we will migrate the token assignment data. But a **copy** will be created,
so the privacyIDEA system still works on the existing assignment.

Run

    ./migrate-data.py

This can be run several times while still running 2.23.5 and
adding new token assignments.

**Note:** Run the script from your virtualenv. It assumes, that your config is
located in ``/etc/privacyidea/pi.cfg``.

privacyIDEA 2.23.5 still runs on the assignments in the token table. So
if new tokens are assigned, the tokenowner table will not reflect this.
Consecutive runs of ``migrate-data.py`` will only migrate the token data, of tokens,
that have not been assigned, yet.

**Note:** If token assignments have been changed in the meantime (token assigned to
*another* user), the script will - for performance reasons - not reflect this!

## Step 3: Update privacyIDEA

Now privacyIDEA can be updated to version >= 3.2.x.

You can do this using the normal update mechanism via ``apt`` or ``yum``.

At this point, the alembic_version of the schema should ensure,
that the normal update procedure does not run the migration script for the
token assignment again. It will rather add all subsequent database changes.

## Step 4: Remove old columns

The old columns of the token assignment in table "token" can be dropped
manually:

* user_id
* resolver
* resolver_type
