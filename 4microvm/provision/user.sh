#!/bin/bash
# User provisioning for the agent harness VM. Runs as the Lima user.
set -euo pipefail

if [ ! -x /usr/local/bin/dsh ]; then
    echo "dsh is not installed; system provisioning did not complete" >&2
    exit 1
fi

mkdir -p "$HOME/.codex" "$HOME/.dsh" "$HOME/.cache/native-binaries"

# The system provisioner enabled lingering so this user manager survives
# logout and starts on boot. Set an explicit runtime environment for cloud-init.
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
export DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR/bus"
if ! systemctl --user is-active --quiet docker.service; then
    dockerd-rootless-setuptool.sh install
fi
systemctl --user daemon-reload
bash /opt/agent-config/bin/setup-shared-dev-db

install -m 0644 /opt/agent-config/codex/config.toml "$HOME/.codex/config.toml"
ln -sfn /opt/agent-config/AGENTS.md "$HOME/.codex/AGENTS.md"
ln -sfn /opt/agent-config/AGENTS.md "$HOME/.dsh/AGENTS.md"

git config --global user.name "Agent"
git config --global user.email "agent@localhost"
git config --global init.defaultBranch main
git config --global --unset-all credential.helper >/dev/null 2>&1 || true

# Lima uses this file for host -> guest SSH. Never ship a private key.
if [ -d "$HOME/.ssh" ]; then
    find "$HOME/.ssh" -maxdepth 1 -type f \( -name 'id_*' -o -name '*_rsa' -o -name '*_ed25519' \) -delete
fi

cat <<'EOF'

Harness VM provisioning complete. Open a shell and run codex or dsh.
Codex login: codex login --device-auth
EOF
