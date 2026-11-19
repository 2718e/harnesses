# Shared development database

## Connect

From `4microvm` on the host:

```sh
just shell
shared-db my_project
export DATABASE_URL="${SHARED_DEV_DB_BASE_URL}my_project"
```

`shared-db` creates the named database or reports that it already exists. It
works from any directory. Names start with a letter or underscore, contain letters,
digits or underscores, and are at most 63 characters. The base URL includes
credentials and a trailing slash and is exported in guest login shells. For a
process that does not read shell profiles, source
`/mnt/lima-agvm-p/config/connection.env` explicitly. This file and
`shared-dev-db.env` contain credentials and are private to the guest user.
PostgreSQL listens on guest loopback; its port is not forwarded to the host.

## Refresh from GitHub

With the VM running, from `4microvm` on the host:

```sh
just update-shared-dev-db
```

This fetches a fresh shallow checkout, builds the image before stopping the
service, snapshots runtime files on the persistent disk, and restarts the service.
It preserves database files and credentials, but briefly interrupts connections.
The default branch is `main`; only changes pushed there are fetched. To select another remote branch for one refresh, run in the
guest:

```sh
SHARED_DEV_DB_BRANCH=main bash /opt/agent-config/bin/setup-shared-dev-db
```

Alternatively, `SHARED_DEV_DB_SOURCE=/path/to/checkout bash
/opt/agent-config/bin/setup-shared-dev-db` uses a checkout visible in the guest.
`just setup` also refreshes the runtime. Normal boots use the persistent snapshot
and do not need network access.

Existing credentials are preserved. Settings pointing at the older `postgres/`
path are rejected: review the settings and migrate old data deliberately before
using `postgres18/`. PostgreSQL major versions cannot use one another's data
without an upgrade. If database files exist without settings or a rootless
identity record, setup fails instead of inventing credentials or recursively
changing owners. A changed rootless mapping also fails. None of these cases
automatically deletes data.

## Extensions

The image includes PostGIS. Enable it separately in each project database with
`CREATE EXTENSION IF NOT EXISTS postgis;`. Availability does not enable it for
all databases. Refreshing the image preserves database data and credentials.
See the shared-dev-db documentation for build options and extension upgrades.
