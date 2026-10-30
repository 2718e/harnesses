# Agent VM and persistent database

The VM uses rootless Docker Engine and Compose. Both the Docker daemon and the
database service run as the guest user; the system Docker daemon and socket are
masked, and the agent is not added to the Docker group. Rootless Docker uses
Linux user namespaces and does not make the VM a substitute for a security
boundary. The guest user manager uses lingering to start services at boot.

The tracked VM definition declares the read-only `/opt/agent-config` mount.
The `just` launcher derives its host path from this checkout and combines it
with the optional mounts in `mountavm.yaml`. An identical legacy entry in the
local file is accepted; conflicts and overlapping mounts are rejected. Both
creation and `just update-mounts` require Python and PyYAML on the host. Keep
the host checkout available while the VM is running: the mount is live.

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
settings. Existing data on the old VM's primary disk is not transferred. The
persistent disk records the guest UID, GID, and subordinate UID/GID ranges on
first provisioning. A later VM with a different mapping refuses to start the
database rather than silently using the wrong file owners. Existing database
files with no mapping record, such as data made by rootful Docker, require a
separate migration; do not change their ownership recursively without a backup.

## Database service

On first provisioning, the VM clones the committed state of the read-only
repository at `/projects/shared-dev-db` into
`/mnt/lima-pgdata/shared-dev-db`. Commit the desired database-project changes
before recreating the VM: a Git clone does not include uncommitted edits.
The service uses the persistent checkout, so later boots and VM recreations do
not depend on the source mount. It is not updated automatically. To update it,
stop the database service and deliberately fetch and fast-forward the checkout;
the initial `origin` is the mounted repository and can later be changed to a
remote URL. Whether the agent can edit a separate project mount is independent
of this checkout.

After creating the VM, in its shell create a private configuration on the
persistent disk:

```sh
cd /mnt/lima-pgdata/shared-dev-db
umask 077
# Only if no configuration file exists; preserve an existing password.
cp .env.example /mnt/lima-pgdata/config/shared-dev-db.env
# Edit the file: choose a private POSTGRES_PASSWORD and set:
# POSTGRES_DATA_DIR=/mnt/lima-pgdata/postgres18
# Remove any POSTGRES_IMAGE override for the old 17 image.
```

Start the database for the first time with:

```sh
docker compose --project-name shared-dev-db \
  --env-file /mnt/lima-pgdata/config/shared-dev-db.env config --quiet
# After confirming the checkout uses PostgreSQL 18 and the data path above:
touch /mnt/lima-pgdata/config/postgres18-ready
systemctl --user start shared-dev-db.service
COMPOSE_ENV_FILE=/mnt/lima-pgdata/config/shared-dev-db.env \
  ./scripts/create-db.sh my_project
```

The user systemd service starts the Compose project on boot and retries if the
disk, configuration, checkout, or database health check is not ready. It uses an
override to prevent Docker from starting the database before the disk is
mounted. The database container is not automatically restarted after a crash;
restart it with `systemctl --user restart shared-dev-db.service`. The data and
settings persist on the disk. If startup fails, inspect
`systemctl --user status shared-dev-db.service` and
`journalctl --user -u shared-dev-db.service`.
The data directory and password in this example are separate from the host
instance. Keep the database bound to guest loopback unless remote access is
deliberately configured.

The `postgres18-ready` file is a one-time opt-in to automatic startup after
checking the 18 configuration. For a previous 17 test, change the existing
environment file to `postgres18` before creating it. The old data remains in
`/mnt/lima-pgdata/postgres`; no disk reset or deletion is necessary. PostgreSQL
major versions cannot use one another's data without a proper upgrade.

The parent data directory allows traversal by the container's PostgreSQL user;
the PostgreSQL data directory inside it remains private (mode 0700). This is
needed because the image starts as container root, then switches to its own
PostgreSQL user before initialization.

## Verify after provisioning

Run these commands in the guest shell:

```sh
docker info --format '{{json .SecurityOptions}}'
systemctl --user status docker.service shared-dev-db.service --no-pager
systemctl is-enabled docker.service docker.socket
id
sudo -n true  # should fail
docker -H unix:///var/run/docker.sock info  # should fail
findmnt /mnt/lima-pgdata
```

Docker's security options should include `rootless`, and the agent must not be
in the `docker` group. A writable project mount can be tested by creating a
throwaway file both directly and in a rootless container, then comparing their
numeric owners with `stat -c '%n %u:%g' FILE` on host and guest. Container
images running as non-root may use subordinate IDs and produce different host
ownership; test the actual images used by your projects.

To test persistence, create a project database with the helper, add a small test
table, run `just recreate` on the host, and query the table again in the new
VM. Check the service logs above if it does not start. `just recreate` deletes
the VM's primary disk and logins; only the separate `pgdata` disk is retained.
