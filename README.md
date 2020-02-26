# migrate-2.23.5-to-3.0

Tools to offline migrate privacyIDEA 2.23.5 to privacyIDEA 3.0

see https://github.com/privacyidea/privacyidea/issues/2040

In contrast to privacyIDEA 2.23.5 privacyIDEA 3.0 now stores the user assignments
in the database table "tokenowner".
While the migration scripts take care of this, in setups with tens of thousands
of users, this could take quite a time.
These tools are ment to prepare the database schema and the data in the database
so that the update of the software runs faster.

The migrations would be done in two steps:

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
At this point, the alembic_version of the schema should ensure,
that the normal update procedure does not run the migration script again.

## Step 4: Remove old columns

The old columns of the token assignment in table "token" can be dropped
manually:

* user_id
* resolver
* resolver_type
