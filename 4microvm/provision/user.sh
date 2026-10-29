#!/bin/bash
# User provisioning for the agent harness VM. Runs as the Lima user.
set -euo pipefail

mkdir -p "$HOME/.codex" "$HOME/.dsh" "$HOME/.config/systemd/user" "$HOME/.cache/native-binaries"

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

cat > "$HOME/.config/systemd/user/dsh.service" <<'EOF'
[Unit]
Description=dsh web
[Service]
Environment=DSH_HOME=%h/.dsh
Environment=DSH_TELEMETRY_MODE=DISABLED
Environment=DSH_PERMISSION_MODE=danger-full-access
Environment=UV_PROJECT_ENVIRONMENT=.venv-agent-container
Environment=UV_LINK_MODE=copy
Environment=PNPM_HOME=%h/.local/share/pnpm
Environment=NPM_CONFIG_PREFIX=%h/.local
Environment=GIT_TERMINAL_PROMPT=0
Environment=NARB_NATIVE_CACHE_DIR=%h/.cache/native-binaries
Environment=PATH=/opt/harness/node_modules/.bin:%h/.local/bin:%h/.local/share/pnpm:/usr/local/bin:/usr/bin:/bin
WorkingDirectory=/projects
ExecStart=/usr/local/bin/dsh web --no-open --port 3081 --trusted-host localhost --trusted-host 127.0.0.1
Restart=on-failure
RestartSec=2
[Install]
WantedBy=default.target
EOF

# Enable the unit through the filesystem as well, so it still starts on the
# next login/reboot if the user manager is not running during provisioning.
mkdir -p "$HOME/.config/systemd/user/default.target.wants"
ln -sfn "$HOME/.config/systemd/user/dsh.service" "$HOME/.config/systemd/user/default.target.wants/dsh.service"

export XDG_RUNTIME_DIR="/run/user/$(id -u)"
if systemctl --user daemon-reload 2>/dev/null; then
    systemctl --user enable dsh >/dev/null 2>&1 || true
    if ! systemctl --user restart dsh 2>/dev/null; then
        echo "warning: dsh user service is enabled but not running yet; it will start after login/reboot" >&2
    fi
else
    echo "warning: user systemd is not available yet; dsh will start after login/reboot" >&2
fi

cat <<'EOF'

Harness VM provisioning complete.

Codex login (from a dsh terminal or limactl shell):
  codex login --device-auth
or use the browser flow; guest port 1455 is forwarded to the host.

dsh logs:
  journalctl --user -u dsh

dsh URL:
  just url   (from the host)
EOF
