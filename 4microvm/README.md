# Agent VM and persistent database

With Lima, uv, just, and virtiofsd installed on the host, put `harnesses` and
`shared-dev-db` checkouts beside each other, then run from this directory:

```sh
just setup
```

This creates the persistent 20 GiB `agentvm-db` disk if missing, creates or starts
`agentvm`, generates private database credentials once, and waits for PostgreSQL
to become healthy. `just create` is an alias. Rerunning preserves the disk,
credentials, and databases; it refreshes the database runtime files and restarts
the database service, briefly interrupting connections.

No `mountavm.yaml` is needed for the base VM and database. To add project mounts,
copy `mountavm.example.yaml` to `mountavm.yaml` and edit the paths before setup.
A read-only `/projects/shared-dev-db` entry can select another source checkout;
otherwise the launcher uses the sibling repository. The launcher supplies
`/opt/agent-config` from this harness checkout. Keep the harness checkout
available while the VM runs, since its config mount is live. Do not mount the
active harness checkout as a writable project; use a separate clone instead.
Conflicting and overlapping mounts are rejected.

## Use the database

```sh
just shell
shared-db my_project
# SHARED_DEV_DB_BASE_URL already includes credentials and a trailing slash.
# Supply a project-specific URL to your application:
export DATABASE_URL="${SHARED_DEV_DB_BASE_URL}my_project"
```

`shared-db` creates the named database or reports that it already exists. It
works from any directory. Database names start with a letter or underscore,
contain letters, digits or underscores, and are at most 63 characters.
The base URL is exported in guest login shells without choosing a database
for every project. For a process that does not read shell profiles, source
`/mnt/lima-agentvm-db/config/connection.env` explicitly. Both this file and
`shared-dev-db.env` contain credentials and are private to the guest user.
PostgreSQL listens on guest loopback; its port is not forwarded to the host.

## Persistence and lifecycle

`just stop` and `just start` handle normal use; the database starts at boot.
`just delete` removes only the VM. `just recreate` rebuilds guest state and
logins while retaining `agentvm-db`, and refuses to delete an existing VM if its
persistent disk is missing. Both setup and recreation validate the proposed
configuration before creating disks or deleting an instance.

For a fresh database, stop the VM and run `just delete-db` to permanently
delete the entire `agentvm-db` disk, including all databases and credentials.
`just nuke` deletes the VM first, then that disk. Run `just setup` afterward
to create both from scratch. These commands do not affect a host-side database.

Lima keeps the disk under `LIMA_HOME`, rather than
`/media/dan/data/databases`; check available storage there. To choose another
initial size, run `just create-db-disk 40GiB` before `just setup`. The automatic
path never resizes or replaces an existing disk. Never delete `agentvm-db` while its
data is needed. Back up PostgreSQL independently; a separate disk is not a backup.

The persistent disk stores:

- `postgres18/`: PostgreSQL data, mounted at `/var/lib/postgresql` in the container.
- `config/shared-dev-db.env`: instance settings and generated password.
- `config/connection.env`: shell export of the connection base URL.
- `config/rootless-identity`: guest UID/GID and subordinate ID mapping.
- `shared-dev-db/`: a snapshot of the source repository's Compose file and runtime scripts.

Setup copies the current runtime files, including uncommitted edits, without
copying host credentials, database files, or Git metadata. Normal boots use the
persistent snapshot and do not need the source database mount. Run `just setup`
after deliberately changing database runtime code. It preserves settings; edits
to the source `.env` are unrelated to the VM instance.

An older VM needs `just recreate` to receive these provisioning and service
changes; setup does not rewrite a saved instance's disk/provisioning definition.
`just update-mounts` updates only shared directory mounts in a stopped VM, then
`just start` uses them. An identical legacy required mount is accepted.

Existing credentials are preserved. Settings pointing at the older `postgres/`
path are rejected: review the settings and migrate old data deliberately before
using `postgres18/`. PostgreSQL major versions cannot use one another's data
without an upgrade. The earlier manual `postgres18-ready` marker is no longer
needed. If database files exist without settings or a rootless identity record,
setup fails instead of inventing new credentials or recursively changing owners.
A changed rootless mapping also fails. None of these cases automatically deletes
data.

## Runtime and troubleshooting

Docker and Compose run as the guest user with rootless Docker. The system daemon
and socket are masked, and the agent is not in the Docker group. User lingering
starts the services at boot. Rootless containers do not make this VM a substitute
for a security boundary.

The systemd user service checks the persistent mount and configuration, then
waits for Compose health. It retries failed startup; the container's own restart
policy is disabled to prevent Docker starting it before the disk is mounted.
To restart after a container crash, run
`systemctl --user restart shared-dev-db.service` in the guest.

```sh
just doctor
just shell
systemctl --user status docker.service shared-dev-db.service --no-pager
journalctl --user -u shared-dev-db.service
```

`docker info --format '{{json .SecurityOptions}}'` should include `rootless`.
`sudo -n true` and `docker -H unix:///var/run/docker.sock info` should fail.
A writable project mount can be tested by creating a throwaway file directly and
in a rootless container, then comparing numeric owners with `stat` on host and
guest. Images running as non-root may produce subordinate IDs; test your actual
project images.

Run `just test` for host-side tests. They check mount merging, setup reruns, and
refusal before destructive recreation. A full persistence check requires Lima:
create a project database and test table, run `just recreate`, then query it in
the new VM. Recreation deletes the primary VM disk and logins.

The disk is named `agentvm-db` because disk names are shared within `LIMA_HOME`.
The short name also avoids older Lima ext4 label bugs. An existing disk named
`pgdata` is not migrated or deleted by these commands; existing VMs need recreation
to use the new name.
