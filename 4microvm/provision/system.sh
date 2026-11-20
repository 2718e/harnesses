#!/bin/bash
# System provisioning for the agent harness VM. Runs as root.
# Must be idempotent: Lima may invoke provisioning more than once.
set -euo pipefail

if [ "$(uname -m)" != "x86_64" ]; then
    echo "this provisioning script currently supports x86_64 only" >&2
    exit 1
fi

export DEBIAN_FRONTEND=noninteractive
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

if [ ! -r /opt/agent-config/versions.env ]; then
    echo "missing /opt/agent-config/versions.env; check the agent-config mount" >&2
    exit 1
fi
source /opt/agent-config/versions.env

# Lima expands this template in provisioning scripts for the configured user.
AGENT_USER="{{.User}}"
if ! id "$AGENT_USER" >/dev/null 2>&1; then
    echo "could not find the Lima guest user: $AGENT_USER" >&2
    exit 1
fi
AGENT_GROUP="$(id -gn "$AGENT_USER")"

echo "provisioning for user $AGENT_USER ($AGENT_GROUP)"

apt-get update
PACKAGES=(
    ca-certificates
    curl
    git
    golang-go
    build-essential
    cmake
    pkg-config
    jq
    just
    ripgrep
    tmux
    fd-find
    unzip
    xz-utils
    python3
    python3-venv
    python3-pip
    sudo
    uidmap
    dbus-user-session
    slirp4netns
    fuse-overlayfs
    qemu-system-x86
    qemu-utils
    ovmf
)
apt-get install -y --no-install-recommends "${PACKAGES[@]}"

# The guest can act as a KVM host for nested Lima instances. Existing login
# sessions must reconnect to acquire the new supplementary group.
usermod -aG kvm "$AGENT_USER"
LIMA_TARBALL="lima-$LIMA_VERSION-Linux-x86_64.tar.gz"
LIMA_TMP_DIR=$(mktemp -d)
curl -fsSLo "$LIMA_TMP_DIR/$LIMA_TARBALL" "https://github.com/lima-vm/lima/releases/download/v$LIMA_VERSION/$LIMA_TARBALL"
printf '%s  %s\n' "$LIMA_SHA256" "$LIMA_TMP_DIR/$LIMA_TARBALL" | sha256sum -c -
tar -xzf "$LIMA_TMP_DIR/$LIMA_TARBALL" -C /usr/local
rm -rf "$LIMA_TMP_DIR"

if [ -x /usr/bin/fdfind ]; then
    ln -sfn /usr/bin/fdfind /usr/local/bin/fd
fi

# Install Tailscale from its official Debian 13 repository. The guest user can
# manage Tailscale; enrollment remains an interactive step.
install -m 0755 -d /usr/share/keyrings
curl -fsSL https://pkgs.tailscale.com/stable/debian/trixie.noarmor.gpg -o /usr/share/keyrings/tailscale-archive-keyring.gpg
curl -fsSL https://pkgs.tailscale.com/stable/debian/trixie.tailscale-keyring.list -o /etc/apt/sources.list.d/tailscale.list
apt-get update
# Mask before package installation so its post-install hook cannot start a daemon
# using disposable root-disk state. Refuse to proceed without the real disk.
systemctl mask tailscaled.service
mountpoint -q /mnt/lima-agvm-p || { echo "persistent disk is not mounted" >&2; exit 1; }
install -d -m 0700 -o root -g root /mnt/lima-agvm-p/tailscale
apt-get install -y tailscale
install -d -m 0755 /etc/systemd/system/tailscaled.service.d
cat > /etc/systemd/system/tailscaled.service.d/persistent-state.conf <<'EOF'
[Unit]
RequiresMountsFor=/mnt/lima-agvm-p
[Service]
ExecStartPre=/usr/bin/mountpoint -q /mnt/lima-agvm-p
ExecStart=
ExecStart=/usr/sbin/tailscaled --state=/mnt/lima-agvm-p/tailscale/tailscaled.state --socket=/run/tailscale/tailscaled.sock --port=${PORT} $FLAGS
EOF
systemctl daemon-reload
systemctl unmask tailscaled.service
systemctl enable --now tailscaled.service
tailscale set --operator="$AGENT_USER" --ssh

# First login can replace preferences configured before enrollment. Wait until
# Tailscale is connected, then apply SSH to the active profile. This service
# does not block VM boot or require tailnet credentials during provisioning.
cat > /usr/local/sbin/enable-tailscale-ssh <<'EOF'
#!/bin/bash
set -euo pipefail
until tailscale status --json 2>/dev/null | python3 -c 'import json, sys; sys.exit(json.load(sys.stdin).get("BackendState") != "Running")' 2>/dev/null; do
    sleep 5
done
tailscale set --ssh
EOF
chmod 0755 /usr/local/sbin/enable-tailscale-ssh
cat > /etc/systemd/system/enable-tailscale-ssh.service <<'EOF'
[Unit]
Description=Enable Tailscale SSH after enrollment
After=tailscaled.service
Requires=tailscaled.service

[Service]
Type=simple
ExecStart=/usr/local/sbin/enable-tailscale-ssh
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now enable-tailscale-ssh.service

# Docker's official Debian packages include the Compose v2 plugin.
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
printf 'deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian trixie stable\n' > /etc/apt/sources.list.d/docker.list
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin docker-ce-rootless-extras
# Default to rootless Docker under the agent's systemd user manager.
# The agent has sudo and can change this configuration.
systemctl disable --now docker.service docker.socket containerd.service || true
systemctl mask docker.service docker.socket
if getent group docker >/dev/null && id -nG "$AGENT_USER" | tr ' ' '\n' | grep -qx docker; then
    gpasswd -d "$AGENT_USER" docker
fi
loginctl enable-linger "$AGENT_USER"

# The disk and its environment file are intentionally independent of the VM.
# User provisioning initializes private settings and starts the service.
if ! mountpoint -q /mnt/lima-agvm-p; then
    echo "persistent agvm-p disk is not mounted; refusing to provision database storage" >&2
    exit 1
fi
install -d -m 0700 -o "$AGENT_USER" -g "$AGENT_GROUP" /mnt/lima-agvm-p/config
# The disk root belongs to root. Create an empty destination the guest user
# can snapshot runtime files into, without changing existing ownership.
if [ ! -e /mnt/lima-agvm-p/shared-dev-db ]; then
    install -d -m 0755 -o "$AGENT_USER" -g "$AGENT_GROUP" /mnt/lima-agvm-p/shared-dev-db
fi
if [ ! -d /mnt/lima-agvm-p/postgres ]; then
    install -d -m 0711 -o "$AGENT_USER" -g "$AGENT_GROUP" /mnt/lima-agvm-p/postgres
fi
if [ ! -d /mnt/lima-agvm-p/postgres18 ]; then
    install -d -m 0711 -o "$AGENT_USER" -g "$AGENT_GROUP" /mnt/lima-agvm-p/postgres18
fi
# Rootless container file owners depend on the guest UID and subordinate ID
# ranges. Refuse to attach old data with a different or unknown mapping.
subuid=$(awk -F: -v user="$AGENT_USER" '$1 == user { print $2 ":" $3 }' /etc/subuid)
subgid=$(awk -F: -v user="$AGENT_USER" '$1 == user { print $2 ":" $3 }' /etc/subgid)
if [ -z "$subuid" ] || [ -z "$subgid" ]; then
    echo "missing subordinate UID/GID ranges for $AGENT_USER" >&2
    exit 1
fi
identity_file=/mnt/lima-agvm-p/config/rootless-identity
identity=$(printf 'uid=%s\ngid=%s\nsubuid=%s\nsubgid=%s' "$(id -u "$AGENT_USER")" "$(id -g "$AGENT_USER")" "$subuid" "$subgid")
if [ -e "$identity_file" ]; then
    if [ "$(cat "$identity_file")" != "$identity" ]; then
        echo "rootless UID/GID mapping changed; refusing to start the existing database" >&2
        exit 1
    fi
else
    if [ -n "$(find /mnt/lima-agvm-p/postgres /mnt/lima-agvm-p/postgres18 -mindepth 1 -maxdepth 1 -print -quit)" ]; then
        echo "existing database data has no rootless identity record; migrate it before continuing" >&2
        exit 1
    fi
    printf '%s\n' "$identity" > "$identity_file"
    chmod 0600 "$identity_file"
    chown "$AGENT_USER:$AGENT_GROUP" "$identity_file"
fi
# The image runs initdb as its postgres user, which must traverse this parent
# directory. PGDATA itself remains private to that user (mode 0700).
chmod 0711 /mnt/lima-agvm-p/postgres
chmod 0711 /mnt/lima-agvm-p/postgres18
install -d -m 0755 /etc/shared-dev-db
cat > /etc/shared-dev-db/compose.yaml <<'EOF'
services:
  postgres:
    # systemd starts it only after checking the persistent disk is mounted.
    restart: "no"
EOF
install -d -m 0755 /etc/systemd/user
cat > /etc/systemd/user/shared-dev-db.service <<'EOF'
[Unit]
Description=Shared development PostgreSQL
Requires=docker.service
After=docker.service
StartLimitIntervalSec=0

[Service]
Type=oneshot
RemainAfterExit=yes
Environment=DOCKER_HOST=unix://%t/docker.sock
WorkingDirectory=/mnt/lima-agvm-p/shared-dev-db
ExecStartPre=/usr/bin/mountpoint -q /mnt/lima-agvm-p
ExecStartPre=/usr/bin/test -f /mnt/lima-agvm-p/config/shared-dev-db.env
ExecStartPre=/usr/bin/test -f /mnt/lima-agvm-p/config/connection.env
ExecStart=/usr/bin/docker compose --project-name shared-dev-db --env-file /mnt/lima-agvm-p/config/shared-dev-db.env -f /mnt/lima-agvm-p/shared-dev-db/compose.yaml -f /etc/shared-dev-db/compose.yaml up -d --wait --wait-timeout 120
ExecStop=/usr/bin/docker compose --project-name shared-dev-db --env-file /mnt/lima-agvm-p/config/shared-dev-db.env -f /mnt/lima-agvm-p/shared-dev-db/compose.yaml -f /etc/shared-dev-db/compose.yaml stop
TimeoutStartSec=0
Restart=on-failure
RestartSec=30

[Install]
WantedBy=default.target
EOF

# Node is installed from a pinned upstream tarball, matching the container setup.
NODE_TARBALL="node-v$NODE_VERSION-linux-x64.tar.xz"
curl -fsSLo "/tmp/$NODE_TARBALL" "https://nodejs.org/dist/v$NODE_VERSION/$NODE_TARBALL"
(
    cd /tmp
    printf '%s  %s\n' "$NODE_SHA256" "$NODE_TARBALL" | sha256sum -c -
)
tar -xJf "/tmp/$NODE_TARBALL" -C /usr/local --strip-components=1
rm -f "/tmp/$NODE_TARBALL"

npm install --global "pnpm@$PNPM_VERSION" "t3@$T3_VERSION"

# uv is installed from a pinned release rather than the floating installer.
UV_TARBALL="uv-x86_64-unknown-linux-gnu.tar.gz"
UV_DIR="uv-x86_64-unknown-linux-gnu"
curl -fsSLo "/tmp/$UV_TARBALL"     "https://github.com/astral-sh/uv/releases/download/$UV_VERSION/$UV_TARBALL"
tar -xzf "/tmp/$UV_TARBALL" -C /tmp
install -m 0755 "/tmp/$UV_DIR/uv" /usr/local/bin/uv
install -m 0755 "/tmp/$UV_DIR/uvx" /usr/local/bin/uvx
rm -rf "/tmp/$UV_TARBALL" "/tmp/$UV_DIR"

# Install the skill installer from its Go module. Go downloads its required
# toolchain automatically if the distribution version is older. Lima system
# provisioning may not set HOME; Go needs it for its module and build caches.
HOME=/root GOBIN=/usr/local/bin go install github.com/owainlewis/skills@latest

# Install the harness Node project. The package files come from the read-only
# agent-config mount; /opt/harness stays root-owned so the agent cannot mutate
# its own harness binaries.
install -d -m 0755 /opt/harness
install -m 0644 /opt/agent-config/harness/package.json /opt/harness/package.json
install -m 0644 /opt/agent-config/harness/pnpm-lock.yaml /opt/harness/pnpm-lock.yaml
install -m 0644 /opt/agent-config/harness/pnpm-workspace.yaml /opt/harness/pnpm-workspace.yaml
(
    cd /opt/harness
    HOME=/root pnpm install --prod --frozen-lockfile --store-dir /tmp/pnpm-store
)
rm -rf /tmp/pnpm-store

for tool in codex ast-grep sg tree-sitter; do
    if [ -e "/opt/harness/node_modules/.bin/$tool" ]; then
        ln -sfn "/opt/harness/node_modules/.bin/$tool" "/usr/local/bin/$tool"
    fi
done

# Mount points. Do not chmod an existing mount:
# /datasets may be read-only and /new-projects may already belong to the host.
[ -d /projects ] || install -d -m 0755 /projects
[ -d /new-projects ] || install -d -m 0775 -o "$AGENT_USER" -g "$AGENT_GROUP" /new-projects
[ -d /datasets ] || install -d -m 0555 /datasets

# Environment for interactive shells opened through limactl.
cat > /etc/profile.d/agent-env.sh <<'EOF'
export PNPM_HOME="$HOME/.local/share/pnpm"
export NPM_CONFIG_PREFIX="$HOME/.local"
export PATH="$HOME/.local/bin:$PNPM_HOME:/opt/harness/node_modules/.bin:$PATH"
export UV_PROJECT_ENVIRONMENT=.venv-agent-container
export UV_LINK_MODE=copy
export GIT_TERMINAL_PROMPT=0
export DOCKER_HOST="unix:///run/user/$(id -u)/docker.sock"
if [ -r /mnt/lima-agvm-p/config/connection.env ]; then
    . /mnt/lima-agvm-p/config/connection.env
fi
EOF
chmod 0644 /etc/profile.d/agent-env.sh
ln -sfn /opt/agent-config/bin/shared-db /usr/local/bin/shared-db

# Grant the guest user passwordless sudo, regardless of Lima's sudo group or
# cloud-init policy. Validate the rule before installing it.
sudo_rule=$(mktemp)
trap 'rm -f "$sudo_rule"' EXIT
printf '%s ALL=(ALL:ALL) NOPASSWD: ALL\n' "$AGENT_USER" > "$sudo_rule"
visudo -cf "$sudo_rule"
install -o root -g root -m 0440 "$sudo_rule" /etc/sudoers.d/99-agentvm-user
visudo -c
if ! su - "$AGENT_USER" -c 'sudo -n true' >/dev/null 2>&1; then
    echo "passwordless sudo is unavailable for $AGENT_USER" >&2
    exit 1
fi

apt-get clean

echo "system provisioning complete"
