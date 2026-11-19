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
The current default branch is `enable-incremental-backups`; only changes pushed
there are fetched. To select another remote branch for one refresh, run in the
guest:

```sh
SHARED_DEV_DB_BRANCH=main bash /opt/agent-config/bin/setup-shared-dev-db
```

Alternatively, `SHARED_DEV_DB_SOURCE=/path/to/checkout bash
/opt/agent-config/bin/setup-shared-dev-db` uses a checkout visible in the guest.
`just setup` also refreshes the runtime. Normal boots use the persistent snapshot
and do not need network access. If backups are enabled, refresh requires a source
containing the backup runtime files.

Existing credentials are preserved. Settings pointing at the older `postgres/`
path are rejected: review the settings and migrate old data deliberately before
using `postgres18/`. PostgreSQL major versions cannot use one another's data
without an upgrade. If database files exist without settings or a rootless
identity record, setup fails instead of inventing credentials or recursively
changing owners. A changed rootless mapping also fails. None of these cases
automatically deletes data.

## Configure backups

These steps enable pgBackRest for the entire PostgreSQL cluster, including future
project databases. They require the backup-capable shared-dev-db branch to be
pushed and fetched as above. The repository stores two full backups and their
dependent backups; these instructions schedule a weekly full and daily incremental
backup. Backups are unencrypted and include all databases. Use a private host
folder on storage separate from the VM's PostgreSQL disk, with sufficient space.

1. On the host, create a dedicated backup directory and add a writable mount to
   `mountavm.yaml`, using the commented example in `mountavm.example.yaml`. The
   guest path in the remaining instructions is `/mnt/shared-dev-db-backups`.
   For an existing VM, stop it, run `just update-mounts`, then `just start`.
   Ensure any host filesystem containing the folder is itself mounted before
   starting the VM; otherwise the folder could refer to the wrong filesystem.

2. Run `just update-shared-dev-db`, then `just shell`. The remaining commands are
   run inside the guest. Verify the guest mount, then let the container's postgres
   user own the *dedicated, initially empty* repository directory. This changes
   ownership and permissions of that host directory through the mount:

   ```sh
   mountpoint -q /mnt/shared-dev-db-backups || { echo 'Backup mount missing'; exit 1; }
   docker run --rm -v /mnt/shared-dev-db-backups:/repo \
     --entrypoint sh shared-dev-db:18-postgis -c 'chown postgres:postgres /repo && chmod 700 /repo'
   docker run --rm -u postgres -v /mnt/shared-dev-db-backups:/repo \
     --entrypoint sh shared-dev-db:18-postgis -c 'f=$(mktemp /repo/.write-test.XXXXXX) && rm "$f"'
   ```

   Rootless Docker maps container IDs to guest/host IDs. If these checks fail,
   resolve mount ownership and access on the host before continuing; do not make
   a sensitive backup directory world-writable. If `POSTGRES_IMAGE` was changed,
   use that image tag instead of `shared-dev-db:18-postgis` above.

3. Install a user-service override so the backup overlay is used at every start
   and startup fails if the guest mount is absent:

   ```sh
   mkdir -p ~/.config/systemd/user/shared-dev-db.service.d
   cat > ~/.config/systemd/user/shared-dev-db.service.d/backup.conf <<'UNIT'
   [Service]
   Environment=BACKUP_REPO_DIR=/mnt/shared-dev-db-backups
   ExecStartPre=/usr/bin/mountpoint -q /mnt/shared-dev-db-backups
   ExecStart=
   ExecStart=/usr/bin/docker compose --project-name shared-dev-db --env-file /mnt/lima-agvm-p/config/shared-dev-db.env -f /mnt/lima-agvm-p/shared-dev-db/compose.yaml -f /etc/shared-dev-db/compose.yaml -f /mnt/lima-agvm-p/shared-dev-db/compose.backup.yaml up -d --wait --wait-timeout 120
   ExecStop=
   ExecStop=/usr/bin/docker compose --project-name shared-dev-db --env-file /mnt/lima-agvm-p/config/shared-dev-db.env -f /mnt/lima-agvm-p/shared-dev-db/compose.yaml -f /etc/shared-dev-db/compose.yaml -f /mnt/lima-agvm-p/shared-dev-db/compose.backup.yaml stop
   UNIT
   systemctl --user daemon-reload
   systemctl --user restart shared-dev-db.service
   ```

   Restarting briefly interrupts database connections. A mountpoint check inside
   the guest cannot detect a host filesystem that was already absent when Lima
   mounted its directory; check the host too.

4. Take and verify the initial full backup. Archiving alone is not a backup:

   ```sh
   export BACKUP_REPO_DIR=/mnt/shared-dev-db-backups
   export COMPOSE_PROJECT_NAME=shared-dev-db
   export COMPOSE_ENV_FILE=/mnt/lima-agvm-p/config/shared-dev-db.env
   bash /mnt/lima-agvm-p/shared-dev-db/scripts/backup.sh full
   docker compose --project-name shared-dev-db --env-file "$COMPOSE_ENV_FILE" \
     -f /mnt/lima-agvm-p/shared-dev-db/compose.yaml \
     -f /mnt/lima-agvm-p/shared-dev-db/compose.backup.yaml \
     exec -T -u postgres postgres pgbackrest --stanza=shared-dev-db info
   ```

   To run a backup manually later, use the same exports and the script with
   `full`, `diff`, or `incr`. Do not continue to scheduling until the full
   backup succeeds and appears in `info`.

5. Install timers in the guest. The full runs Sunday at 02:00 and the incremental
   runs daily at 03:00 in the guest's local timezone. Persistent timers run missed
   jobs after the user service manager starts. If jobs overlap, pgBackRest's lock
   can cause one to fail; adjust the schedule for the size of your database.

   ```sh
   mkdir -p ~/.config/systemd/user
   cat > ~/.config/systemd/user/shared-dev-db-backup@.service <<'UNIT'
   [Unit]
   Description=Shared database %i backup
   Requires=shared-dev-db.service
   After=shared-dev-db.service

   [Service]
   Type=oneshot
   Environment=DOCKER_HOST=unix://%t/docker.sock
   Environment=BACKUP_REPO_DIR=/mnt/shared-dev-db-backups
   Environment=COMPOSE_PROJECT_NAME=shared-dev-db
   Environment=COMPOSE_ENV_FILE=/mnt/lima-agvm-p/config/shared-dev-db.env
   ExecStartPre=/usr/bin/mountpoint -q /mnt/shared-dev-db-backups
   ExecStart=/bin/bash /mnt/lima-agvm-p/shared-dev-db/scripts/backup.sh %i
   UNIT
   cat > ~/.config/systemd/user/shared-dev-db-backup-full.timer <<'UNIT'
   [Unit]
   Description=Weekly shared database full backup
   [Timer]
   OnCalendar=Sun *-*-* 02:00:00
   Persistent=true
   Unit=shared-dev-db-backup@full.service
   [Install]
   WantedBy=timers.target
   UNIT
   cat > ~/.config/systemd/user/shared-dev-db-backup-incr.timer <<'UNIT'
   [Unit]
   Description=Daily shared database incremental backup
   [Timer]
   OnCalendar=*-*-* 03:00:00
   Persistent=true
   Unit=shared-dev-db-backup@incr.service
   [Install]
   WantedBy=timers.target
   UNIT
   systemctl --user daemon-reload
   systemctl --user enable --now shared-dev-db-backup-full.timer shared-dev-db-backup-incr.timer
   systemctl --user list-timers 'shared-dev-db-backup*'
   ```

Check `journalctl --user -u 'shared-dev-db-backup@*'` and backup age regularly;
a timer does not guarantee a successful backup. Monitor available space on both
the backup and PostgreSQL disks: failed WAL archiving can fill the database disk.
Test restores periodically using the [pgBackRest restore guide](https://pgbackrest.org/user-guide.html#restore)
and a separate, empty data directory. Keep instance settings and credentials
separately; they are not included in physical backups.

The override and timers live on the guest's primary disk and are lost on `just
recreate`. Reapply them after recreation, verify the host mount and permissions,
and check the existing repository before resuming backups. The backup directory
itself is on the host and is not removed by VM recreation.

## Extensions

The image includes PostGIS. Enable it separately in each project database with
`CREATE EXTENSION IF NOT EXISTS postgis;`. Availability does not enable it for
all databases. Refreshing the image preserves database data and credentials.
See the shared-dev-db documentation for build options and extension upgrades.
