# Agent VM and persistent database

The VM uses Docker Engine and Compose. The guest user is in the Docker group;
this gives the agent root-equivalent control of the guest through Docker, even
though it has no sudo access. Treat the VM as the security boundary.

## Persistent disk and VM lifecycle

Create the separate 20 GiB Lima disk once, before creating the VM:

```sh
just create-db-disk
just create
```

An optional size can be passed to `just create-db-disk`, for example
`just create-db-disk 40GiB`. Lima stores this disk in its own disk directory
under `LIMA_HOME`; it is not currently placed under
`/media/dan/data/databases`. Check the available storage there before creating
it. The disk appears in the guest at `/mnt/lima-pgdata` as an ext4 filesystem.

`just recreate` deletes the VM and its guest state, including logins, but not
the separate `pgdata` disk. It checks for that disk first. `just delete` also
leaves the disk in place. Never run `limactl disk delete pgdata` if its data is
needed. Back up the database independently; a separate disk is not a backup.

An existing instance uses its own saved Lima configuration and its original
provisioning. Create the disk and recreate the VM to apply these changes;
`update-mounts` only updates shared directory mounts, not disk or provisioning
settings. Existing data on the old VM's primary disk is not transferred.

## Database service

The database repository is mounted read-only at `/projects/shared-dev-db` so
the VM can use its Compose definition. Whether to let the agent edit that
repository is a separate choice from database storage and operation.

After creating the VM, in its shell create a private configuration on the
persistent disk:

```sh
cd /projects/shared-dev-db
umask 077
cp .env.example /mnt/lima-pgdata/config/shared-dev-db.env
# Edit the file: choose a private POSTGRES_PASSWORD and set:
# POSTGRES_DATA_DIR=/mnt/lima-pgdata/postgres
```

Start the database for the first time with:

```sh
docker compose --project-name shared-dev-db \
  --env-file /mnt/lima-pgdata/config/shared-dev-db.env \
  -f compose.yaml -f /etc/shared-dev-db/compose.yaml up -d
COMPOSE_ENV_FILE=/mnt/lima-pgdata/config/shared-dev-db.env \
  ./scripts/create-db.sh my_project
```

The installed systemd service starts the same Compose project on subsequent VM
boots when the disk and environment file are present. It uses an override to
prevent Docker from starting the database before the disk is mounted. The VM's
data and settings persist on the disk, so recreating the VM does not require
recreating the databases or settings. If startup fails, inspect
`systemctl status shared-dev-db.service` and `journalctl -u shared-dev-db.service`.
The data directory and password in this example are separate from the host
instance. Keep the database bound to guest loopback unless remote access is
deliberately configured.
