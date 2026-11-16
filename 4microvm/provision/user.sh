#!/bin/bash
# User provisioning for the agent harness VM. Runs as the Lima user.
set -euo pipefail

mkdir -p "$HOME/.codex"

# The system provisioner enabled lingering so this user manager survives
# logout and starts on boot. Set an explicit runtime environment for cloud-init.
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
export DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR/bus"
if ! systemctl --user is-active --quiet docker.service; then
    dockerd-rootless-setuptool.sh install
fi
systemctl --user daemon-reload
bash /opt/agent-config/bin/setup-shared-dev-db

bash /opt/agent-config/bin/sync-agent-config

# Install only the project setup skill globally from the mounted Git checkout.
/usr/local/bin/skills add /opt/skills-repo --agent agents --skill baseline-setup --global --yes

git config --global user.name "Agent"
git config --global user.email "agent@localhost"
git config --global init.defaultBranch main
git config --global --unset-all credential.helper >/dev/null 2>&1 || true

# Lima uses this file for host -> guest SSH. Never ship a private key.
if [ -d "$HOME/.ssh" ]; then
    find "$HOME/.ssh" -maxdepth 1 -type f \( -name 'id_*' -o -name '*_rsa' -o -name '*_ed25519' \) -delete
fi

cat <<'EOF'

Harness VM provisioning complete. Open a shell and run codex.
Codex login: codex login --device-auth
EOF
