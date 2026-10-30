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
    build-essential
    cmake
    pkg-config
    jq
    ripgrep
    fd-find
    unzip
    xz-utils
    python3
    python3-venv
    python3-pip
    sudo
)
apt-get install -y --no-install-recommends "${PACKAGES[@]}"

if [ -x /usr/bin/fdfind ]; then
    ln -sfn /usr/bin/fdfind /usr/local/bin/fd
fi

if ! command -v nerdctl >/dev/null 2>&1 && ! command -v nerdctl.lima >/dev/null 2>&1; then
    echo "warning: nerdctl not found; rootless containerd may not be installed" >&2
fi

# Node is installed from a pinned upstream tarball, matching the container setup.
NODE_TARBALL="node-v$NODE_VERSION-linux-x64.tar.xz"
curl -fsSLo "/tmp/$NODE_TARBALL" "https://nodejs.org/dist/v$NODE_VERSION/$NODE_TARBALL"
(
    cd /tmp
    printf '%s  %s\n' "$NODE_SHA256" "$NODE_TARBALL" | sha256sum -c -
)
tar -xJf "/tmp/$NODE_TARBALL" -C /usr/local --strip-components=1
rm -f "/tmp/$NODE_TARBALL"

npm install --global "pnpm@$PNPM_VERSION"

# uv is installed from a pinned release rather than the floating installer.
UV_TARBALL="uv-x86_64-unknown-linux-gnu.tar.gz"
UV_DIR="uv-x86_64-unknown-linux-gnu"
curl -fsSLo "/tmp/$UV_TARBALL"     "https://github.com/astral-sh/uv/releases/download/$UV_VERSION/$UV_TARBALL"
tar -xzf "/tmp/$UV_TARBALL" -C /tmp
install -m 0755 "/tmp/$UV_DIR/uv" /usr/local/bin/uv
install -m 0755 "/tmp/$UV_DIR/uvx" /usr/local/bin/uvx
rm -rf "/tmp/$UV_TARBALL" "/tmp/$UV_DIR"

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

if [ ! -f /opt/harness/node_modules/@deepseek-ai/dsh/lib/bin.js ]; then
    echo "dsh is missing from /opt/harness; pnpm install did not complete" >&2
    exit 1
fi

cat > /usr/local/bin/dsh <<'EOF'
#!/bin/sh
exec node --expose-internals /opt/harness/node_modules/@deepseek-ai/dsh/lib/bin.js "$@"
EOF
chmod 0755 /usr/local/bin/dsh

for tool in codex ast-grep sg tree-sitter; do
    if [ -e "/opt/harness/node_modules/.bin/$tool" ]; then
        ln -sfn "/opt/harness/node_modules/.bin/$tool" "/usr/local/bin/$tool"
    fi
done

# Mount points and the dsh working directory. Do not chmod an existing mount:
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
export DSH_TELEMETRY_MODE=DISABLED
export DSH_PERMISSION_MODE=danger-full-access
export NARB_NATIVE_CACHE_DIR="$HOME/.cache/native-binaries"
export GIT_TERMINAL_PROMPT=0
EOF
chmod 0644 /etc/profile.d/agent-env.sh

# Remove the agent's sudo authorization. Lima needs passwordless sudo during
# first boot, but the agent must not keep it afterwards.
deluser "$AGENT_USER" sudo || true
rm -f /etc/sudoers.d/90-cloud-init-users
visudo -c
if su - "$AGENT_USER" -c 'sudo -n true' >/dev/null 2>&1; then
    echo "sudo is still available for $AGENT_USER" >&2
    exit 1
fi

apt-get clean

echo "system provisioning complete"
