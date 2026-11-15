# Agent harness VM — implementation plan (Phases 1–3)

- **Status:** implemented, 2026-10-29
- **Scope:** Lima VM, Codex and dsh, provisioning, mounts. Stops at the end of Phase 3.
- **Supersedes:** Phases 1–3 of the [earlier plan](agent_in_vm_setup.md). The later phases of that file are not part of this plan.

## Decisions from the review

| Topic | Decision |
| --- | --- |
| Firecracker / microVM | Out of scope. Lima is the chosen platform. |
| Cross-harness subagents | Out of scope. Do not build dsh↔Codex delegation in this iteration. |
| Codex in a browser | Use the dsh web terminal sidebar. No ttyd, tmux or other terminal service. |
| Docker | Do not install Docker. Use Lima's rootless containerd + nerdctl. |
| Codex install | Yes, use the same package.json/pnpm install as dsh. |
| Mount updates | Edit the Lima instance YAML directly. A just recipe updates mounts and refuses to run while the VM is running. |
| sudo for the agent | No. Remove the agent user from sudo at the end of provisioning. |
| dsh port | 3081 on the guest and host, so the container version can keep 3080. |
| virtiofsd | Host prerequisite, documented only. Do not attempt to validate host-only requirements from the container. |

## Host prerequisites (documented, not automated)

These are host-side facts. The implementation cannot check them from this container, so they belong in the runbook, not in a provisioning check.

- Lima with QEMU and KVM.
- **Rust virtiofsd** if mountType is virtiofs. On Debian 13: sudo apt install virtiofsd. The QEMU-packaged qemu-virtiofsd is not a substitute. If it is missing, use mountType: 9p and accept lower performance.
- Ports 3081 and 1455 free on the host loopback. 1455 is only for the Codex browser-login callback.
- python3-yaml on the host for the update-mounts helper. This is the one small host-side dependency beyond Lima.

## 1. Target layout

~~~
4microvm/
  agentvm.yaml                 # generic VM: image, resources, containerd, ports, provision
  mountavm.example.yaml        # tracked example; copy to mountavm.yaml and edit paths
  mountavm.yaml                # host-specific, gitignored; contains ALL mounts
  provision/
    system.sh                  # root: packages, Node, pnpm, uv, harness install, sudo removal
    user.sh                    # user: Codex/dsh config, user systemd unit, git identity
  agent-config/
    AGENTS.md                  # shared harness instructions
    versions.env               # Node, pnpm and uv pins
    codex/config.toml
    harness/
      package.json             # dsh, Codex, ast-grep, tree-sitter
      pnpm-lock.yaml
      pnpm-workspace.yaml      # pnpm 12 build allowlist
  scripts/
    update_mounts.py           # host-side helper; edits the instance YAML
  justfile
~~~

There is deliberately no Docker-specific setup, no dsh skills directory and no terminal service yet. Those can be added after the base VM works.

## 2. Phase 1 — VM definition and provisioning

### 2.1 agentvm.yaml

Keep host-specific paths out of the generic file. All mounts live in mountavm.yaml instead; this avoids relying on how Lima merges arrays from a base file.

~~~yaml
base:
  - template:_images/debian-13

vmType: qemu
cpus: 4
memory: 8GiB
disk: 60GiB

# Lima's default rootless containerd. No Docker daemon.
containerd:
  user: true
  system: false

# virtiofs is better for node_modules. Requires Rust virtiofsd on the host.
# Use 9p if virtiofsd is unavailable or unstable.
mountType: virtiofs
mountInotify: true

portForwards:
  - guestPort: 3081
    hostPort: 3081
    hostIP: 127.0.0.1
  - guestPort: 1455
    hostPort: 1455
    hostIP: 127.0.0.1

provision:
  - mode: system
    file: ./provision/system.sh
  - mode: user
    file: ./provision/user.sh
~~~

Notes:

- Do not set containerd: none. Lima's rootless containerd provides nerdctl, BuildKit, runc and CNI plugins. This is the container runtime for the agents.
- Do not set user.passwordlessSudo: false. On Linux that requires plain: true, which disables mounts and port forwarding. Sudo is removed in system provisioning instead (section 2.4).
- The agent user is the Lima-created user, which defaults to the host account name and uid 1000. Do not create a second user.

### 2.2 Harness as one Node package

Yes, Codex can be installed from package.json. The official npm package is @openai/codex. Keep dsh, Codex and the two code tools in one pnpm project under agent-config/harness.

~~~json
{
  "private": true,
  "engines": { "node": ">=24" },
  "dependencies": {
    "@deepseek-ai/dsh": "0.2.1-rc.2",
    "@openai/codex": "0.165.0",
    "@ast-grep/cli": "0.51.0",
    "tree-sitter-cli": "0.27.1"
  }
}
~~~

- Codex has platform-specific optional dependencies. pnpm installs the Linux x64 package automatically.
- pnpm 12 no longer reads the pnpm field in package.json. Build-script permissions live in pnpm-workspace.yaml under allowBuilds.
- Several dsh dependencies also need build scripts, not just the code tools. The tested allowlist is @ast-grep/cli, @deepseek-ai/dsh-subprocess-local, @google/genai, koffi, node-pty, protobufjs and tree-sitter-cli, all set to true. Without them pnpm fails with ERR_PNPM_IGNORED_BUILDS.
- Commit pnpm-lock.yaml and pnpm-workspace.yaml. Regenerate the lockfile when bumping versions.

pnpm-workspace.yaml:

~~~yaml
allowBuilds:
  "@ast-grep/cli": true
  "@deepseek-ai/dsh-subprocess-local": true
  "@google/genai": true
  koffi: true
  node-pty: true
  protobufjs: true
  tree-sitter-cli: true
~~~
- Install with:
  ~~~
  pnpm install --prod --frozen-lockfile --store-dir /tmp/pnpm-store
  ~~~
  Remove /tmp/pnpm-store afterwards.
- The install lives at /opt/harness, owned by root. The agent cannot modify its own harness binaries. Updating versions means recreating the VM, which is the intended reproducible path.
- Expose the tools through /usr/local/bin: a dsh wrapper using node --expose-internals, and symlinks for codex, ast-grep, sg and tree-sitter. Do not rely only on PATH for interactive shells.

### 2.3 system.sh

Runs as root. It must be idempotent because Lima may invoke provision scripts more than once.

1. Install base packages: ca-certificates, curl, git, build-essential, pkg-config, jq, ripgrep, fd-find, unzip, python3, python3-venv, python3-pip. Do not install docker.io, docker-compose or a docker group.
2. Install Node 24 from a pinned official tarball into /usr/local. Pin the exact version in agent-config/versions.env. This also provides npm.
3. Install pnpm at the pinned version globally.
4. Install uv into /usr/local/bin from a pinned release.
5. Copy agent-config/harness to /opt/harness (including pnpm-workspace.yaml), then pnpm install as above.
6. Create the dsh wrapper and tool symlinks in /usr/local/bin.
7. Enable lingering for the agent user so a user systemd service can run at boot:
   ~~~
   loginctl enable-linger "$AGENT_USER"
   ~~~
8. Create /projects, /new-projects and /datasets so mount points and WorkingDirectory always exist.
9. Write /etc/profile.d/agent-env.sh for interactive shells:
   ~~~
   export PNPM_HOME="$HOME/.local/share/pnpm"
   export NPM_CONFIG_PREFIX="$HOME/.local"
   export PATH="$HOME/.local/bin:$PNPM_HOME:/opt/harness/node_modules/.bin:$PATH"
   export UV_PROJECT_ENVIRONMENT=.venv-agent-container
   export UV_LINK_MODE=copy
   export DSH_TELEMETRY_MODE=DISABLED
   export DSH_PERMISSION_MODE=danger-full-access
   export GIT_TERMINAL_PROMPT=0
   ~~~
10. Disable sudo for the agent user (section 2.4).

Do not install a system-wide dsh service. Because the agent has no sudo, a user unit is needed so dsh can be restarted without root.

### 2.4 Removing sudo

Keep the sudo binary installed but remove the agent's authorization. This preserves a normal Debian user account while preventing every privileged operation.

At the end of system.sh:

~~~
AGENT_USER="$(id -un 1000)"
deluser "$AGENT_USER" sudo || true
rm -f /etc/sudoers.d/90-cloud-init-users
visudo -c
if su - "$AGENT_USER" -c 'sudo -n true' 2>/dev/null; then
  echo "sudo is still available for $AGENT_USER" >&2
  exit 1
fi
~~~

Adjust the cloud-init sudoers filename if the image uses a different one; check /etc/sudoers.d if the test above fails. The test is part of provisioning because it runs inside the guest.

Trade-offs:

| Capability | With sudo | Without sudo (chosen) |
| --- | --- | --- |
| apt / system packages | Yes | No; add to provisioning and recreate |
| Rootful nerdctl | Yes | No; rootless nerdctl only |
| System systemd units | Yes | No; user units only |
| Privileged ports below 1024 | Yes | No; use 3081 and other high ports |
| Write host mounts as root | Yes, risk of root-owned files | No |
| User-local tools, uv, pnpm, rustup, project deps | Yes | Yes |
| Rootless containers and builds | Yes | Yes |

Consequences:

- The baseline environment matters more. If an agent needs a system package, the host updates provisioning and recreates the VM. This is the reproducibility cost.
- Project docs that say apt-get install or docker ... will fail. AGENTS.md must say so explicitly.
- Installing a compiler toolchain is still possible user-locally (rustup, uv tool, npm prefix, Go tarball). Only system packages are blocked.
- No sudo means no root-owned files on mounted project paths. That directly removes the earlier permission risk.
- Codex and dsh still run as an unprivileged Unix user. Their danger-full-access / never settings remove harness-level sandbox prompts; they do not grant Unix privileges.

### 2.5 user.sh

Runs as the agent user, not root.

1. Copy agent-config/codex/config.toml to ~/.codex/config.toml. Copy, do not symlink: Codex may rewrite its config.
2. Symlink agent-config/AGENTS.md to ~/.codex/AGENTS.md and ~/.dsh/AGENTS.md.
3. Set a neutral git identity, init.defaultBranch=main, and no credential helper. Do not create SSH keys. Remove any id_* files if the image happens to contain them.
4. Write ~/.config/systemd/user/dsh.service and enable it.
5. Print the Codex login instructions and the dsh log command.

No dsh cordis.patch.yml is needed initially. Use DSH_PERMISSION_MODE from the environment. If the pinned dsh version stops honoring it, add the patch then.

## 3. Phase 2 — harness configuration

### 3.1 dsh user service on 3081

~~~ini
[Unit]
Description=dsh web
[Service]
Environment=DSH_HOME=%h/.dsh
Environment=DSH_TELEMETRY_MODE=DISABLED
Environment=DSH_PERMISSION_MODE=danger-full-access
Environment=UV_PROJECT_ENVIRONMENT=.venv-agent-container
Environment=UV_LINK_MODE=copy
Environment=NARB_NATIVE_CACHE_DIR=%h/.cache/native-binaries
Environment=PATH=/opt/harness/node_modules/.bin:%h/.local/bin:/usr/local/bin:/usr/bin:/bin
WorkingDirectory=/projects
ExecStart=/usr/local/bin/dsh web --no-open --port 3081 --trusted-host localhost --trusted-host 127.0.0.1
Restart=on-failure
RestartSec=2
[Install]
WantedBy=default.target
~~~

- Install it under ~/.config/systemd/user/dsh.service.
- Enable with:
  ~~~
  export XDG_RUNTIME_DIR="/run/user/$(id -u)"
  systemctl --user daemon-reload
  systemctl --user enable --now dsh
  ~~~
- If the user manager is not available during first-boot provisioning, enable the unit and let the first login or reboot start it; do not make provisioning fail.
- Check the installed dsh version supports --port. If it does not, use its documented port setting, but keep 3081.
- The token URL is printed to the user journal. The just url recipe reads journalctl --user -u dsh.
- The container version keeps 3080, so both can run at once.

### 3.2 Codex config

~~~toml
approval_policy = "never"
sandbox_mode = "danger-full-access"
check_for_update_on_startup = false

[projects."/projects"]
trust_level = "trusted"

[projects."/new-projects"]
trust_level = "trusted"
~~~

This is the "already sandboxed by the VM" setting. The Unix user is still unprivileged and sudo is unavailable, so full access inside the harness does not mean root.

Codex login:

- Prefer codex login --device-auth.
- Otherwise use the normal browser flow; guest port 1455 is forwarded to host 1455 for the callback.
- Do not put auth.json in provisioning or in a shared snapshot.

### 3.3 Shared AGENTS.md

Minimum content:

- This is a Lima VM. The host is not directly reachable except through mounts.
- Mount table and which paths are read-only.
- No sudo and no system-wide systemctl. Do not run sudo, apt, or docker. User-level systemctl (systemctl --user) is available if you need to restart dsh. Use user-local installs.
- Containers: rootless nerdctl. nerdctl run, nerdctl build, nerdctl compose. No Docker socket.
- Package installs: pnpm/npm into the project or the user prefix; uv for Python; rustup/uv tool for user tools. System packages require a provisioning change and VM recreation.
- Python: use uv. The project venv is .venv-agent-container so the host .venv is never touched.
- Node: use pnpm. Global installs go under ~/.local.
- Git: no host SSH keys or credentials. Local branches and worktrees work; pushes do not. The host can recover from the remote.
- Tools available: rg, ast-grep/sg, tree-sitter, jq, uv, pnpm.
- dsh web is on 3081. Codex is available from the dsh terminal sidebar; no separate terminal service.
- Do not write into read-only mounts.

## 4. Phase 3 — mounts and project lifecycle

### 4.1 All mounts in mountavm.yaml

Put every mount, including agent-config, in the host-specific file. The generic agentvm.yaml has no mounts. This makes update-mounts deterministic and avoids the Lima base/array merge question.

~~~yaml
base:
  - ./agentvm.yaml

mounts:
  - location: "/home/USER/dev/harnesses/4microvm/agent-config"
    mountPoint: "/opt/agent-config"
    writable: false

  - location: "/home/USER/dev/property-search"
    mountPoint: "/projects/property-search"
    writable: true

  - location: "/home/USER/dev/shared-dev-db"
    mountPoint: "/projects/shared-dev-db"
    writable: false   # reference only

  - location: "/home/USER/dev/_new"
    mountPoint: "/new-projects"
    writable: true

  - location: "/home/USER/dev/datasets"
    mountPoint: "/datasets"
    writable: false
~~~

Rules:

- No two mountPoints may overlap (for example, /projects and /projects/foo).
- No two host locations may overlap for the same reason.
- /new-projects must not sit under a project mount.
- The agent-config location must point at the checked-out agent-config directory. If the repo moves, update it.
- Keep mountavm.yaml gitignored and commit mountavm.example.yaml with placeholders.

### 4.2 update-mounts

Directly editing the instance file is fine. limactl edit is only an editor/wrapper around ~/.lima/agentvm/lima.yaml. The instance file, not mountavm.yaml, is what Lima reads on start.

Add scripts/update_mounts.py and a just recipe:

~~~
update-mounts:
    @python3 scripts/update_mounts.py agentvm mountavm.yaml
    @echo "Mounts updated. Run 'just start'."
~~~

The helper:

1. Uses limactl list --json to find the instance status and its directory. The instance YAML is at DIR/lima.yaml, or LIMA_HOME/agentvm/lima.yaml if the JSON field is unavailable.
2. Exits nonzero with a clear message if the instance is Running. It must not edit a live VM.
3. Loads mountavm.yaml, validates the mounts list (required location and mountPoint, no duplicate or nested mountPoints, no nested host locations).
4. Replaces the instance YAML's mounts list with the validated source list. Because all mounts are in the source, this also removes entries deleted from the source.
5. Writes the instance YAML atomically.

Host dependency: python3-yaml (Debian python3-yaml). If installing a YAML parser on the host is undesirable, the same helper can be written against yq, but do not hand-edit YAML with sed.

This design gives the requested behaviour:

- update-mounts adds new mounts from mountavm.yaml.
- It also applies changed writable flags and removes deleted mounts.
- It errors while the VM is running.
- It does not require limactl edit.
- It does not touch portForwards, cpus or memory; those still need a recreate.

### 4.3 New projects

Use the single /new-projects writable mount.

- Agent creates /new-projects/foo.
- Host sees it immediately.
- To promote it, move the directory to its real host location, stop the VM, add a mount entry to mountavm.yaml, run update-mounts, and start.
- Do not mount the whole dev/ parent. Lima has no exclusions and overlapping mounts are not supported.

### 4.4 justfile recipes

Keep these small and host-side:

- create: limactl start --name=agentvm ./mountavm.yaml
- start / stop / restart / shell / delete
- recreate: delete --force then create. This is how provisioning changes are applied.
- update-mounts: as above.
- url: read the token URL from journalctl --user -u dsh in the guest, on port 3081.
- logs: journalctl --user -u dsh -f.
- sync-config: limactl copy the tracked config into the guest, then systemctl --user restart dsh with XDG_RUNTIME_DIR set.
- delete: limactl delete --force agentvm.

All user-systemd and user-journal commands need XDG_RUNTIME_DIR=/run/user/$(id -u), including url and logs.

Replace the current restart.sh with these recipes. Keep mountavm.yaml in .gitignore; add mountavm.example.yaml.

## 5. Verification

### Container-side checks (do these while implementing)

- bash -n provision/system.sh provision/user.sh
- python3 -m py_compile scripts/update_mounts.py
- Parse agent-config/harness/package.json as JSON.
- Validate the example YAML syntax with a local parser if available.
- Check that no Docker, tmux, ttyd or cross-harness delegation remains in the scripts and AGENTS.md.
- Check that all mount points are distinct and non-nested.
- Check that the dsh service uses 3081 and the container path remains 3080.

### Host-side checks (deferred; do not attempt from the container)

- virtiofsd is installed on the host.
- limactl start succeeds and mounts appear.
- Read-only mounts reject writes.
- The agent cannot sudo and cannot create root-owned files on the host.
- nerdctl run --rm hello-world and a small nerdctl build work rootless.
- dsh is reachable on 3081 with its token URL.
- codex starts from a dsh terminal; device auth or the 1455 callback works.
- update-mounts refuses to run while the VM is up and applies a new mount after stop.

## 6. Risks and open questions

- **No sudo is a real constraint.** If the baseline is incomplete, the agent cannot fix it in place. Mitigate by adding packages to provisioning before a task and recreating. Do not add a broad sudoers exemption later without revisiting the threat model.
- **Rootless nerdctl is not Docker.** Docker Engine API, docker.sock, and some Compose features will not work. If a specific project needs them, that is an explicit exception, not a default.
- **User systemd under Lima.** If the user manager does not start reliably at first boot, fall back to a system unit and accept that dsh restarts require a VM restart, or add a small user-level supervisor. Do not give the agent sudo just to manage dsh.
- **virtiofs performance/stability.** If it is unreliable on the host, switch to 9p and record the node_modules cost.
- **dsh version drift.** DSH_PERMISSION_MODE and --port are current-version behaviours. Verify on the pinned 0.2.1-rc.2; if they change, use the documented config instead of guessing.
- **Codex package layout.** The npm package's platform optional dependency must install correctly under pnpm. If it does not, fall back to the official installer for Codex only and document why.
- **8 GiB / 4 CPU may be tight** for two harnesses plus rootless builds. Adjust after the first real workload.

## 7. Out of scope

- Firecracker and any microVM work.
- Cross-harness subagents or shared MCP/ACP bridges.
- Docker Engine or a docker group.
- ttyd, tmux and dedicated Codex browser services. Codex runs in the dsh terminal sidebar.
- Claude Code.
- API keys, host logins and auth automation.
- Per-task dynamic mounts without a VM restart.

## Sources

- Lima filesystem mounts (virtiofs, 9p, mountInotify): https://lima-vm.io/docs/config/mount/
- Lima sudo behaviour: https://lima-vm.io/docs/config/sudo/
- Lima default template (containerd, provision, mounts): https://github.com/lima-vm/lima/blob/master/templates/default.yaml
- Codex npm package: https://www.npmjs.com/package/@openai/codex
- Codex approvals and sandbox: https://learn.chatgpt.com/docs/agent-approvals-security
- Codex authentication: https://learn.chatgpt.com/docs/auth
- dsh npm package: https://www.npmjs.com/package/@deepseek-ai/dsh
