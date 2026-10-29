# Agent harness VM

Lima VM for running Codex and dsh against explicitly mounted host projects.
The VM has its own kernel, so rootless containers work without exposing the host.

## Host prerequisites

- Lima with QEMU and KVM.
- just on the host.
- Rust virtiofsd for mountType: virtiofs:
  ~~~
  sudo apt install virtiofsd
  ~~~
  The QEMU-packaged qemu-virtiofsd is not a substitute. If virtiofsd is not
  available, change mountType in agentvm.yaml to 9p.
- python3-yaml on the host for scripts/update_mounts.py.
- Host ports 3081 and 1455 free. 1455 is only for the Codex login callback.

## First setup

~~~
cp mountavm.example.yaml mountavm.yaml
$EDITOR mountavm.yaml
just create
just url
~~~

mountavm.yaml is host-specific and gitignored. It must contain every mount,
including the agent-config mount. Do not make mount points or host locations
overlap. Create every host location before first start, for example:

~~~
mkdir -p /media/dan/data/dev/_new
~~~

## Daily commands

~~~
just start
just stop
just shell
just url
just logs
~~~

dsh listens on guest and host port 3081. The container version can keep 3080.

## Mounts

Add or change a project in mountavm.yaml, then:

~~~
just stop
just update-mounts
just start
~~~

update-mounts edits the Lima instance YAML directly and refuses to run while
the VM is running. It replaces the instance mount list with mountavm.yaml, so
removing an entry from the file removes that mount.

New projects can be created in /new-projects. Promote one by moving it on the
host, adding a mount entry, and running the commands above.

## Harnesses

Codex is installed under /opt/harness from the same pnpm project as dsh.
Log in from a dsh terminal or limactl shell:

~~~
codex login --device-auth
~~~

The browser flow also works; guest port 1455 is forwarded to the host.

dsh runs as a user systemd service. Its token URL is printed to the user
journal and can be read with just url.

## Containers and privileges

There is no Docker daemon. Use rootless nerdctl, which Lima's containerd
provides:

~~~
nerdctl run --rm hello-world
nerdctl build -t example .
nerdctl compose up
~~~

The agent does not have sudo. System packages are part of provisioning; add
them to provision/system.sh and recreate the VM. User-local installs through
uv, pnpm/npm and rustup still work.

## Updating

- Provisioning or package versions: edit the files and run just recreate.
  Guest state and Codex/dsh logins are lost.
- Codex config: edit agent-config/codex/config.toml, then just sync-config.
- AGENTS.md: it is symlinked from /opt/agent-config, so changes apply to new
  sessions without a restart.

## Deliberately not included

- Docker Engine.
- Firecracker or other microVMs.
- Cross-harness subagents.
- ttyd or tmux; Codex is used from the dsh terminal sidebar.
