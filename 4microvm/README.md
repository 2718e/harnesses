# Agent VM and persistent storage

With Lima, uv, just, and virtiofsd installed on the host, put `harnesses` and
`shared-dev-db` checkouts beside each other, then run from this directory:

```sh
just setup
```

This creates the persistent 20 GiB `agentvm-persist` disk if missing, creates or starts
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

VM startup waits up to 30 minutes for provisioning. If it times out, inspect
the existing VM before recreating it: `limactl list agentvm`, then, if it is
running, `limactl shell agentvm -- cloud-init status --long` and
`limactl shell agentvm -- sudo tail -100 /var/log/cloud-init-output.log`.
A startup timeout alone does not show whether provisioning succeeded.

## Harness configuration and skills

Provisioning installs the [skills CLI](https://github.com/owainlewis/skills)
and uses it to install only `opinionated-setup` globally into `~/.agents/skills`
for Codex, from the public [2718e/skills repository](https://github.com/2718e/skills).
The installer needs network access during VM creation. Other skills can be
installed per project with the `skills` command.

A local skills checkout is not required for provisioning. To edit it from the
VM, add it as a writable project mount in `mountavm.yaml`. For an existing VM,
stop it and run `just update-mounts` to apply mount changes. Recreate the VM to
install the new global skill; `just sync-config` refreshes Codex configuration
only. Recreation replaces the guest's primary disk and logins but retains the
persistent disk. Restart Codex after changing installed skills.

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
`/mnt/lima-agentvm-persist/config/connection.env` explicitly. Both this file and
`shared-dev-db.env` contain credentials and are private to the guest user.
PostgreSQL listens on guest loopback; its port is not forwarded to the host.

## Remote access

New VMs have Tailscale installed, its daemon enabled, and Tailscale SSH
configured. The guest user is the Tailscale operator. To enroll the VM, run `tailscale up` in `just shell` and
follow the sign-in link. A background service enables Tailscale SSH after
the VM connects; this can take a few seconds. Install Tailscale on your remote device and sign it
into the same tailnet, then connect using `ssh GUEST_USER@VM_TAILSCALE_NAME`.
The tailnet's network and SSH access rules must allow the connection.

Tailscale has an upstream issue where an operator configured before the first
login may still be denied access to `tailscale up` or `tailscale login`. If
that happens, run `sudo tailscale up` instead. Tailscale state lives on the
persistent disk and survives recreation. Key expiry,
revocation or tailnet policy may still require reauthentication. Never run two
VMs using copies of the same Tailscale identity.

### T3 Code

The guest has a pinned T3 Code CLI and `just`. Log in to Codex as the guest
user, then start T3 from a guest shell or tmux session:

```sh
codex login --device-auth
t3 serve --tailscale-serve
```

Follow the pairing link or code shown by T3 on a device in the same tailnet.
Tailscale HTTPS and Serve must be enabled for your tailnet, and its policies
must permit access. Stop the foreground server with Ctrl-C; a tmux session can
keep it running after disconnect. Alternatively, use T3's desktop-managed SSH
connection over Tailscale. See the [T3 remote access guide](https://github.com/pingdotgg/t3code/blob/main/docs/user/remote-access.md).
T3 state, Codex login and sessions, and tmux sessions are lost on VM recreation;
Tailscale SSH and tmux remain available independently of T3.

## Persistence and lifecycle

`just stop` and `just start` handle normal use; the database starts at boot.
`just delete` removes only the VM. `just recreate` rebuilds guest state and
logins while retaining `agentvm-persist`, and refuses to delete an existing VM if its
persistent disk is missing. Both setup and recreation validate the proposed
configuration before creating disks or deleting an instance.

For a fresh database, stop the VM and run `just delete-persistent-disk` to permanently
delete the entire `agentvm-persist` disk, including all databases, credentials and the Tailscale identity.
`just nuke` asks for confirmation before deleting the VM first, then that disk.
Declining or providing no answer leaves both intact. Run `just setup` afterward
to create both from scratch. These commands do not affect a host-side database.

Lima keeps the disk under `LIMA_HOME`, rather than
`/media/dan/data/databases`; check available storage there. To choose another
initial size, run `just create-persistent-disk 40GiB` before `just setup`. The automatic
path never resizes or replaces an existing disk. Never delete `agentvm-persist` while its
data is needed. Back up PostgreSQL independently; a separate disk is not a backup.

The persistent disk stores:

- `tailscale/`: root-only Tailscale device state and credentials.
- `postgres18/`: PostgreSQL data, mounted at `/var/lib/postgresql` in the container.
- `config/shared-dev-db.env`: instance settings and generated password.
- `config/connection.env`: shell export of the connection base URL.
- `config/rootless-identity`: guest UID/GID and subordinate ID mapping.
- `shared-dev-db/`: a snapshot of the source repository's Compose file, Dockerfile and runtime scripts.

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

The guest user has passwordless sudo, including when running Codex. Guest root
can read or change persistent Tailscale credentials and databases, modify guest
security settings, and interact with mounted projects. Take care when deciding
which host directories to mount into the VM.

Docker and Compose default to rootless Docker as the guest user. The system
daemon and socket are initially masked; a user with sudo can change that. User
lingering starts the rootless services at boot.

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
`sudo -n true` should succeed, while `docker -H unix:///var/run/docker.sock info`
should fail under the default rootless configuration.
A writable project mount can be tested by creating a throwaway file directly and
in a rootless container, then comparing numeric owners with `stat` on host and
guest. Images running as non-root may produce subordinate IDs; test your actual
project images.

Run `just test` for host-side tests. They check mount merging, setup reruns, and
refusal before destructive recreation. A full persistence check requires Lima:
create a project database and test table, run `just recreate`, then query it in
the new VM. Recreation deletes the primary VM disk and logins.

### Transition from the old disk

The disk is named `agentvm-persist` to stay within the ext4 label limit on older
Lima versions. The old `agentvm-db` disk and instance are not renamed or deleted
automatically. Setup refuses to replace an existing VM without the new disk, and
refuses to create the new disk when the old disk is present.

If the old database and Tailscale identity are not needed, stop and delete the
old VM, delete its disk, then create the new setup:

```sh
limactl stop agentvm
limactl delete --force agentvm
limactl disk delete agentvm-db
just setup
```

These commands permanently discard the old guest, its logins and old disk
contents. Enroll Tailscale once on the new VM. If you need the old Tailscale
identity, do not delete the old VM: its `/var/lib/tailscale/tailscaled.state`
is root-only in the legacy VM, whose guest user has no sudo. A privileged recovery/migration
procedure is not automated; preserve the VM and disk until the state can be
copied securely while the daemon is stopped. Never copy it to a location readable
by the guest user. The legacy `pgdata` disk is also untouched.

### Database extensions

The shared-dev-db repository builds its PostgreSQL Alpine image with PostGIS;
geospatial packages are installed in the container, so no VM packages or VM
recreation are needed. Setup builds before stopping the current server, then
preserves its persistent data and credentials. Normal boots reuse the built image.
After updating both checkouts, rerun `bash /opt/agent-config/bin/setup-shared-dev-db`.
For a writable guest clone, set `SHARED_DEV_DB_SOURCE=/new-projects/shared-dev-db-postgis`
when invoking setup. The default remains the mounted checkout.

Extensions are enabled per database: connect to the project database and run
`CREATE EXTENSION IF NOT EXISTS postgis;`. Availability in the server does not
enable it in every project database. See shared-dev-db's README for build options.
