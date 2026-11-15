# Agent harness VM — refined implementation plan

- **Status:** proposed, 2026-10-29; **Phases 1–3 superseded** by [agent_in_vm_setup_phases_1-3.md](agent_in_vm_setup_phases_1-3.md).
  The implementation now uses Lima + rootless nerdctl (no Docker), no Firecracker, and no cross-harness subagents. The later-phase sections below are historical.
- **Refines:** the early notes that were in this file
- **Complements:** `dsh/.agent-writing/plans/2026-10-16-self-hosted-microvm-for-dsh.md`
- **Goal:** one reproducible Lima VM with Codex and dsh preconfigured, Docker working inside, and host projects exposed only through explicit mounts.

## Bottom line

Lima is the right base for this iteration. It is a full VM rather than a microVM, but it already provides the property that motivated the change: a separate kernel, so Docker runs normally inside and the host filesystem is visible only through explicit mounts. Firecracker/Cloud Hypervisor remain a later optimisation, not a prerequisite.

What is feasible now:

- Codex and dsh installed and configured from provisioning scripts.
- Docker, git, rg, tree-sitter and ast-grep available in the guest.
- Multiple project mounts, with read-only mounts enforced by the guest kernel.
- A dedicated writable /new-projects mount for projects the agent creates; the host sees them immediately.
- dsh web reachable from the host browser through Lima port forwarding.
- Codex usable from a browser through a terminal-over-web shim (ttyd + tmux), not through an official Codex web UI.

What needs a design decision, not just more provisioning:

- **Task-scoped mount subsets.** Mounts are part of the VM definition. Changing which projects are read-only means stopping the VM, editing mounts, and starting it again. Per-run harness sandboxing can approximate it, but is not the same as a kernel read-only mount.
- **Codex in the browser.** There is no local Codex web client. The realistic options are a terminal in the browser, the dsh terminal sidebar, or building a UI on the Codex app-server. The first is small; the last is a project.
- **Cross-harness subagents.** Direct MCP is not available in either direction today: Codex removed codex mcp-server, and dsh exposes ACP rather than MCP. CLI hand-off works now; a first-class bridge is the next step.

What is not worth doing now:

- Mounting all of dev/ with exclusions. Lima has no mount exclusions and disallows overlapping mounts.
- Replacing Lima with a custom microVM before the harness workflow is settled.
- Building a native Codex web UI.

## 1. Target shape

~~~
host (Debian, KVM)
└── Lima VM "agentvm" (QEMU, Debian 13)
    ├── systemd
    │   ├── docker.service
    │   ├── dsh.service          dsh web on guest 127.0.0.1:3080
    │   └── ttyd.service         optional: Codex TUI on guest 127.0.0.1:7681
    ├── agent user (uid 1000, same as host)
    │   ├── ~/.dsh               DSH_HOME, profiles, sessions
    │   ├── ~/.codex             CODEX_HOME, config, auth
    │   └── ~/.local/bin         uv and user tools
    └── mounts
        ├── /projects/<name>     selected projects, writable or read-only
        ├── /datasets            read-only reference data
        ├── /new-projects        writable staging area
        └── /opt/agent-config    read-only harness config from this repo
~~~

Principles:

- The VM is the security boundary. Inside it the agent may be root; do not try to make guest-side controls a security boundary.
- Host paths are allow-listed by mounts. Home, SSH keys and git credentials are never mounted.
- Harness state (DSH_HOME, CODEX_HOME, Docker images) lives on the guest disk. A recreated VM starts clean; snapshots preserve state.
- Provisioning owns the base environment. Agent-installed packages are allowed, but are disposable until promoted into provisioning.

## 2. Feasibility decisions

| Idea | Verdict | Decision |
| --- | --- | --- |
| Multiple projects | Yes | One mount per project. Default reference projects to writable: false; only active projects are writable. |
| Subsets per task | Partial | Mount changes require stop/edit/start. For a soft per-run restriction, use Codex's sandbox writable roots and dsh's workspace-write mode. Do not pretend this is a hard boundary. |
| New project creation | Yes | Mount one host new-projects directory writable at /new-projects. Promote a project later by adding a dedicated mount. |
| Codex in browser | Partial | No official local web UI. Use ttyd + tmux, or attach the tmux session in dsh web's terminal. Codex app-server is JSON-RPC, not a UI. |
| dsh in browser | Yes | Already supported by dsh web; Lima forwards the guest loopback port. |
| dsh ↔ Codex as subagents | Partial | Use codex exec / dsh --profile headless behind thin wrappers. A first-class bridge needs a small MCP/app-server adapter. |
| Claude Code later | Yes, slot reserved | Same pattern: install CLI, terminal-over-web, optional claude mcp serve for dsh. |
| Language runtimes | Yes, baseline | Node 24, Python 3.13, uv, build tools. Skip mise initially; add it only if real projects need multiple versions. |
| MicroVM (Firecracker) | Later | Do not block on it. Lima is enough for Docker + isolation. Cloud Hypervisor is the upgrade path if footprint matters. |

### 2.1 Projects and read-only mounts

Lima's writable: false is a real kernel read-only mount. That is the only enforcement worth relying on for "do not modify this project".

- Read-only: writable: false (the default).
- Writable: writable: true.
- Datasets: read-only.
- New projects: one writable staging mount.

Changing mounts on an existing instance: edit the **instance** config (limactl edit agentvm) or recreate it. Editing mountavm.yaml after creation does nothing; Lima copies the definition into ~/.lima/agentvm/lima.yaml at create time. This is a common footgun and should be documented in the justfile.

For a temporary read-only task without remounting:

- **Codex:** launch with --sandbox workspace-write and writable roots limited to the active project. Codex's sandbox is OS-enforced for its child processes.
- **dsh:** launch with DSH_PERMISSION_MODE=workspace-write and the workspace root set to the active project. This limits writes for that session; it is not a substitute for a read-only mount.

If a hard guarantee is required, stop the VM, change the mount to writable: false, and start it again.

### 2.2 New projects

The workable options are:

1. **One /new-projects mount (recommended).** The agent creates directories there; the host sees them immediately. Later, the host moves the project to its real location and adds a dedicated mount if it should remain visible.
2. **Mount the whole dev/ parent.** Rejected: Lima has no exclusion list, overlapping mounts are not supported, and it exposes every project by default.
3. **Sync/rsync or git-based transfer.** Rejected as the default. limactl shell --sync is useful for a no-mount, review-before-apply workflow, but it does not fit a long-running dsh web service.

Keep /new-projects outside all project mounts so overlapping paths cannot occur.

### 2.3 Codex in the browser

There is no local Codex web UI. Options, cheapest first:

1. **ttyd + tmux (recommended first cut).** Run Codex in a tmux session, serve it with ttyd on guest 127.0.0.1:7681, forward to host loopback. ttyd supports HTTP basic auth. This is a terminal in a browser, which is enough for Codex's TUI.
2. **dsh web terminal.** If dsh's terminal sidebar can attach to the same tmux session, no extra service is needed. Verify on the installed dsh version before choosing it as the only path.
3. **Codex app-server + custom client.** codex app-server --listen ws://127.0.0.1:4500 is a JSON-RPC API for rich clients. It is not a web UI and is explicitly experimental. Only do this if a terminal is not enough.

Codex login on the VM:

- Prefer codex login --device-auth (beta; may need enabling in account settings).
- Otherwise forward guest port 1455 to host 1455 for the OAuth callback and use the normal browser flow.
- Do not bake ~/.codex/auth.json into the provisioning scripts or snapshots that are shared.

### 2.4 Cross-harness subagents

Important correction to the earlier assumption: **codex mcp-server has been removed.** Codex now exposes an app-server (JSON-RPC) and an MCP *client*. dsh exposes an MCP *client* and an ACP *server*. So neither harness can call the other over MCP out of the box.

What works today:

| From → to | Mechanism | Notes |
| --- | --- | --- |
| dsh → Codex | shell tool runs codex exec --json --skip-git-repo-check ... | One-shot delegation; no live steering or approval bridge. |
| dsh → Claude Code | claude mcp serve via dsh-mcp-client (verify availability) | Only when Claude Code is added. |
| Codex → dsh | shell tool runs dsh --profile headless "..." | One-shot; dsh must be authenticated in the VM. |
| Codex → Claude Code | claude mcp serve via Codex MCP config | MCP is supported on the Codex client side. |
| Claude → Codex / dsh | shell tool runs codex exec / dsh --profile headless | Same wrapper approach. |

Recommended sequence:

1. Ship thin CLI wrappers: run-codex and run-dsh, normalising prompt, cwd, output and exit code. Document them in the shared AGENTS.md. This already gives "use the other harness as a subagent" with no protocol work.
2. If live streaming, approvals, or tool-level integration is needed, build one small MCP server that exposes run_codex and run_dsh (wrapping the same CLIs or Codex app-server). Both harnesses can then consume the same bridge. This is a contained project, not a fork of either harness.

Do not expect model-level interchange. Each harness uses its own account/model. Claude models are not available to the other harnesses through a Claude Code subscription.

### 2.5 Language runtimes

Baseline that is worth preinstalling:

- Node 24 (dsh requires Node; Codex npm package also uses it).
- Python 3.13 + venv + uv.
- build-essential, pkg-config, make, cmake? Keep to build-essential and pkg-config initially; add cmake if a real project needs it.
- Git, curl, ca-certificates, jq, ripgrep, fd-find, unzip.
- Docker Engine + Compose.
- tree-sitter CLI and ast-grep. Prefer pinned npm packages with prebuilt binaries; if tree-sitter has no prebuilt for the guest, add a Rust toolchain or build it in provisioning rather than leaving a half-installed CLI.

Do **not** install mise initially. It can shadow the Node/Python that dsh and the system services rely on, and it adds another version-resolution layer. If multiple versions become a real need, install it as a user-level tool later, not as the system default.

Agent-installed packages are allowed. To keep provisioning useful, add an inventory command (just vm-inventory) that dumps apt history, npm globals, uv tool list, and pip packages so they can be promoted into the scripts deliberately.

## 3. Implementation plan

### Phase 0 — host preconditions and decisions

- Confirm Lima version. Require at least Lima 2.0 for --mount-only and the current AI/MCP features; the existing setup already creates VMs, so this is a check, not a blocker.
- Confirm /dev/kvm, the kvm group, and that the host is not a VM without nested virtualisation.
- Confirm the Rust virtiofsd is installed if mountType: virtiofs is used. Debian 13 ships it; the QEMU-packaged qemu-virtiofsd is not a substitute.
- Decide the host project list and which entries are writable. Record them in mountavm.yaml (host-specific, gitignored) and a tracked mountavm.example.yaml.
- Decide the host port for dsh (default 3080) and make sure the existing dsh container is stopped or moved to another port.

### Phase 1 — provisioning and VM definition

Target layout:

~~~
4microvm/
  agentvm.yaml                 # base: resources, agent-config mount, provision
  mountavm.example.yaml        # tracked example of host project mounts
  mountavm.yaml                # host-specific, gitignored
  versions.env                 # pinned Node, pnpm, dsh, Codex, tool versions
  provision/
    system.sh                  # root: apt, Node, Docker, system tools, services
    user.sh                    # user: uv, pnpm, dsh, Codex, config install
  agent-config/
    AGENTS.md                  # shared harness-level instructions
    codex/config.toml
    dsh/package.json           # dsh as a pinned Node project
    dsh/pnpm-lock.yaml
    dsh/cordis.patch.yml       # only if a patch is needed beyond env vars
    dsh/skills/                # harness-level skills, iterated later
  justfile
~~~

agentvm.yaml shape:

~~~yaml
base:
  - template:_images/debian-13

vmType: qemu
cpus: 4
memory: 8GiB
disk: 60GiB
containerd: none

# virtiofs is better for node_modules; it is experimental on Linux.
# Fall back to 9p if the mount is unstable or virtiofsd is missing.
mountType: virtiofs
mountInotify: true

mounts:
  - location: "{{.Dir}}/agent-config"
    mountPoint: /opt/agent-config
    writable: false

portForwards:
  - guestPort: 3080
    hostPort: 3080
  - guestPort: 7681
    hostPort: 7681
  - guestPort: 1455
    hostPort: 1455

provision:
  - mode: system
    file: ./provision/system.sh
  - mode: user
    file: ./provision/user.sh
~~~

Lima specifics that the implementation must respect:

- file: is resolved relative to the template file and is copied into the instance at create time. Editing a script later does not re-provision an existing VM. Iterate by recreating, or by running the script manually in the guest.
- Provision scripts can be called more than once by Lima, so they must be idempotent.
- {{.Dir}} is available in mounts.location, which keeps the config mount host-independent.
- The base: merge and mounts list should be validated once with limactl validate; if the child file replaces rather than appends mounts, move all mounts into one file.

system.sh responsibilities:

- apt-get update and install: ca-certificates, curl, git, build-essential, pkg-config, jq, ripgrep, fd-find, unzip, tmux, ttyd (optional), docker.io, docker-compose (or the Compose v2 plugin).
- Install Node 24 from a pinned tarball (same approach as dsh/Dockerfile), or NodeSource if the pinned tarball is too much maintenance. Pin the exact version in versions.env.
- Install pnpm at a pinned version.
- Enable and start docker.service; add the agent user to the docker group.
- Create /projects, /new-projects and /datasets so the dsh working directory and mount points always exist.
- Install uv to /usr/local/bin or the user's ~/.local/bin.
- Install the dsh systemd unit and, optionally, the ttyd unit.
- Set system-wide environment defaults in /etc/environment or a profile drop-in:
  - UV_PROJECT_ENVIRONMENT=.venv-agent-container
  - UV_LINK_MODE=copy
  - DSH_TELEMETRY_MODE=DISABLED
  - GIT_TERMINAL_PROMPT=0

user.sh responsibilities:

- Install Codex from the pinned npm package: npm install -g @openai/codex@VERSION.
- Install dsh as a local Node project under /opt/dsh from agent-config/dsh/package.json and pnpm-lock.yaml, then expose a wrapper:

~~~sh
#!/bin/sh
exec node --expose-internals /opt/dsh/node_modules/@deepseek-ai/dsh/lib/bin.js "$@"
~~~

- Copy (not symlink) codex/config.toml to ~/.codex/config.toml and dsh/cordis.patch.yml to ~/.dsh/cordis.patch.yml. These are files a harness may rewrite; the read-only config mount is the source, not the live copy.
- Symlink the shared AGENTS.md to ~/.codex/AGENTS.md and ~/.dsh/AGENTS.md, and link skill directories read-only.
- Install ast-grep and tree-sitter from pinned npm versions, and verify both binaries at the end of provisioning (fail the script if they do not run).
- Set git identity to a neutral VM identity; no credential helper; no SSH keys.
- Create ~/.config/dsh/...? Only if the current dsh version needs it. Prefer environment variables.
- Print or record the dsh URL/token location and the Codex login instructions.

At the current dsh version, the permission mode is already an environment input in the base bundle:

~~~sh
DSH_PERMISSION_MODE=danger-full-access
~~~

That sets the sandbox to full access and approval policy to never. Set it in the dsh service and the login shell. If the installed version no longer reads it, use a home-level cordis.patch.yml and verify with dsh --dump-config. Do not assume the patch shape; check it against the installed version.

### Phase 2 — harness configuration

**dsh service** (system unit, runs as the agent user). Replace `agent` with the Lima user name, which defaults to the host account name; do not create a second user:

~~~ini
[Unit]
Description=dsh web
After=network-online.target docker.service
Wants=network-online.target

[Service]
User=agent
Environment=HOME=/home/agent
Environment=DSH_HOME=/home/agent/.dsh
Environment=DSH_TELEMETRY_MODE=DISABLED
Environment=DSH_PERMISSION_MODE=danger-full-access
Environment=UV_PROJECT_ENVIRONMENT=.venv-agent-container
Environment=UV_LINK_MODE=copy
Environment=PATH=/opt/dsh/node_modules/.bin:/home/agent/.local/bin:/usr/local/bin:/usr/bin:/bin
WorkingDirectory=/projects
ExecStart=/usr/local/bin/dsh web --no-open --trusted-host localhost --trusted-host 127.0.0.1
Restart=on-failure
RestartSec=2

[Install]
WantedBy=multi-user.target
~~~

The dsh URL with token is printed to the journal at startup. just url should read journalctl -u dsh rather than inventing a token.

**Codex config** (~/.codex/config.toml):

~~~toml
approval_policy = "never"
sandbox_mode = "danger-full-access"
check_for_update_on_startup = false

[projects."/projects"]
trust_level = "trusted"

[projects."/new-projects"]
trust_level = "trusted"
~~~

This is deliberately "no guardrails inside the VM". The mount table and the VM boundary are the controls. If the user wants accidental-damage protection instead, switch to sandbox_mode = "workspace-write", set sandbox_workspace_write.writable_roots = ["/projects", "/new-projects"], and network_access = true; note that this also blocks system package installs unless the agent escalates.

**Shared AGENTS.md** should state, at minimum:

- This is a VM; the host is not directly reachable. Mounted paths and their writability.
- Never use sudo to write into /projects or /new-projects; root-owned files on the host are a nuisance to recover.
- No host SSH keys or git credentials. Public clones work; pushes do not. Use branches and worktrees; the host can recover from the remote.
- Docker is available and should be used for container validation.
- rg, ast-grep, tree-sitter, uv, pnpm, jq are installed; tree-sitter grammars may need to be fetched per project.
- Python work uses uv; the project venv is .venv-agent-container so the host .venv is never touched.
- How to hand off to the other harness (see Phase 4).

### Phase 3 — mounts and project lifecycle

Start from the current mountavm.yaml and make the host-specific definition explicit:

~~~yaml
base:
  - ./agentvm.yaml

mounts:
  - location: "/media/dan/data/dev/property-search"
    mountPoint: "/projects/property-search"
    writable: true

  - location: "/media/dan/data/dev/shared-dev-db"
    mountPoint: "/projects/shared-dev-db"
    writable: false   # reference only for this task

  - location: "/media/dan/data/dev/_new"
    mountPoint: "/new-projects"
    writable: true

  - location: "/media/dan/data/dev/datasets"
    mountPoint: "/datasets"
    writable: false
~~~

Do not put /opt/agent-config here if it is already in agentvm.yaml; avoid duplicate/overlapping mounts.

Add just recipes for the lifecycle:

- create: validate host paths, then limactl start --name=agentvm ./mountavm.yaml.
- start, stop, restart, shell, delete.
- recreate: delete and create from scratch. This is the reliable way to apply provisioning changes.
- mounts: show the effective instance config. If automated mount editing is added, it must stop the instance first and use limactl edit.
- url: extract the authenticated dsh URL from the journal.
- sync-config: copy the tracked harness config into the guest and restart dsh.
- snapshot: limactl snapshot create agentvm --tag baseline.
- inventory: dump installed packages for promotion into provisioning.

Mount lifecycle rule: promotion of a new project is a stop → edit → start operation, not a live operation. Document it; do not build an elaborate mount daemon for the first version.

### Phase 4 — optional browser Codex and delegation

Browser Codex (only after the base VM is stable):

- Install ttyd and tmux.
- Run a user service or a manual session: tmux new -A -s codex codex.
- Serve with ttyd -i 127.0.0.1 -p 7681 -W tmux new -A -s codex codex.
- Add basic auth, with the password in a root-only environment file, or rely on host loopback only.
- Lima forwards host 7681 to guest 7681.
- Verify the TUI resize, copy/paste and login flow. If ttyd is poor, try attaching the tmux session in dsh web before building anything custom.

Delegation wrappers:

- run-codex: codex exec --json --skip-git-repo-check --cd <dir> "<prompt>", parse the JSON events, print the final message and exit code.
- run-dsh: dsh --profile headless --cd <dir> "<prompt>" (verify the exact cwd flag on the installed version), print the answer.
- Put both on PATH and document them in AGENTS.md.
- Do not add MCP/ACP plumbing until a real workflow needs streaming or approvals. The current CLI hand-off is enough to prove the pattern.

### Phase 5 — reproducibility and documentation

- Pin every version in versions.env; refresh deliberately. At the time of writing, npm latest is dsh 0.2.1-rc.2 and Codex 0.165.0; re-check before implementation.
- Keep mountavm.yaml host-specific and gitignored; commit mountavm.example.yaml.
- Replace the current restart.sh with the justfile (and remove it from .gitignore if deleted).
- Document the runbook in 4microvm/.agent-writing/docs/MAIN.md (not README.md): create, recreate, add a project, read-only task, login, get the dsh URL, update a version.
- Snapshot after provisioning but before authenticating; treat post-auth snapshots as secret material.
- Recreate the VM at least once from scratch and run the acceptance tests before declaring the setup reproducible.

## 4. Acceptance tests

Run these from the host after a clean just recreate:

1. limactl list shows the VM running; provisioning finished without manual steps.
2. limactl shell agentvm -- codex --version and dsh --version match the pins.
3. curl -fsS http://127.0.0.1:3080/ reaches dsh; the token URL from just url opens the UI.
4. limactl shell agentvm -- codex exec --skip-git-repo-check "print hello" completes without an approval prompt.
5. limactl shell agentvm -- docker run --rm hello-world succeeds.
6. rg --version, ast-grep --version, tree-sitter --version, uv --version, git --version succeed.
7. Create a file on the host under a writable mount; it appears in the guest without a remount. Create a file in the guest; the host file is owned by the host user (not root).
8. touch /datasets/x and touch /projects/<read-only>/x fail with EROFS/EACCES.
9. mkdir /new-projects/test-project appears on the host immediately.
10. In a test repo: git switch -c test, git worktree add ../wt test succeeds; ssh -T git@github.com has no usable key; git push fails without credentials.
11. limactl stop/start brings dsh back and preserves installed packages and harness state.
12. limactl snapshot create agentvm --tag test and restore works (or record why snapshots are unavailable on this host).
13. If virtiofs is used: pnpm install in a test project completes, and a host edit is visible in the guest. Test mountInotify separately and record the watcher gap.

## 5. Risks and gotchas

1. **Editing the source YAML does not update an existing VM.** Lima copies the definition to ~/.lima/agentvm/lima.yaml. Use limactl edit or recreate.
2. **Provisioning is create-time.** file: scripts are stored at create time. Recreate to apply changes, or run them manually.
3. **virtiofs on Linux is experimental.** It needs the Rust virtiofsd. 9p is the stable fallback but slower for node_modules.
4. **No reliable inotify across virtiofs/9p.** mountInotify is experimental and has documented gaps (nested files on 9p, deletes). Watch-mode dev servers may need polling.
5. **Root-owned files on the host.** If the agent writes to a mount via sudo, the host gets root-owned files. Put this in AGENTS.md and test it.
6. **Codex config churn.** codex mcp-server is already gone; app-server is experimental. Pin Codex and re-check the config/auth flow at implementation time.
7. **dsh is on a release candidate.** DSH_PERMISSION_MODE is an implementation detail of the base bundle; verify it on the pinned version and fall back to an explicit patch.
8. **Port conflicts.** The existing dsh compose container uses 3080. Stop it or change the host port.
9. **Auth flow.** Codex device auth is the easiest path; the normal OAuth callback needs guest 1455 forwarded to host 1455. dsh credentials are out of scope.
10. **Snapshots and secrets.** Post-login snapshots contain provider tokens and auth files.
11. **Mount changes are disruptive.** Every subset change is a VM restart; plan tasks around that rather than fighting it.
12. **Host network exposure.** Lima's user-mode network may route guest traffic to host services. Verify from the guest; add host firewall rules if needed.
13. **Git safety is not a security boundary.** No credentials prevents pushes, but a destructive local command can still rewrite a mounted repo. The host's remote is the recovery path; consider per-task branches/worktrees.

## 6. Out of scope for this iteration

- Claude Code installation (leave the mount/config slots and document the pattern).
- Injecting API keys or host logins into the VM.
- A native Codex web UI or a custom Codex app-server client.
- A first-class cross-harness MCP bridge.
- Dynamic per-task mounts without a VM restart.
- Replacing Lima with Cloud Hypervisor/Firecracker.
- Host-side IDE integration and limactl mcp workflows.

## 7. Decisions and open questions

Defaults chosen by this plan:

- **One long-lived VM** running both harnesses, not one VM per task. Per-task VMs can be added later from the same definition.
- **One /new-projects mount** rather than a parent dev/ mount.
- **virtiofs first, 9p fallback**, with a benchmark as the gate.
- **Full access inside the VM** for both harnesses; the VM and mounts are the boundary.
- **CLI hand-off** for cross-harness delegation first; MCP bridge later.
- **ttyd + tmux** for Codex in the browser first; dsh terminal as an alternative.
- **No mise** initially; baseline runtimes only.

Still open, to settle during implementation:

- Does the installed Lima append or replace mounts when a child file uses base:? Validate before relying on the two-file split.
- Does dsh's terminal sidebar attach cleanly to a tmux session? If yes, drop ttyd.
- Is virtiofs stable enough for this host's kernel and workload? Benchmark before committing.
- Is Codex's app-server stable enough to justify a bridge, or are CLI wrappers enough for the foreseeable workflows?
- Should harness state (~/.dsh, ~/.codex) be persisted on a host mount for easy backup, accepting that it contains credentials? Current answer: guest disk + snapshots.

## Sources

- Lima AI agents: https://lima-vm.io/docs/examples/ai/
- Lima filesystem mounts (virtiofs, 9p, mountInotify): https://lima-vm.io/docs/config/mount/
- Lima default template (provision file, mounts, lifecycle): https://github.com/lima-vm/lima/blob/master/templates/default.yaml
- Lima limactl edit: https://lima-vm.io/docs/reference/limactl_edit/
- Lima experimental features: https://lima-vm.io/docs/releases/experimental/
- Codex approvals and sandbox: https://learn.chatgpt.com/docs/agent-approvals-security
- Codex config reference: https://learn.chatgpt.com/docs/config-file/config-reference
- Codex CLI / MCP server removal: https://learn.chatgpt.com/docs/developer-commands
- Codex app-server: https://learn.chatgpt.com/docs/app-server
- Codex authentication (device auth, callback 1455): https://learn.chatgpt.com/docs/auth
- dsh MCP client: @deepseek-ai/dsh-mcp-client README
- dsh ACP profile: @deepseek-ai/dsh-acp-app README
- Prior DSH microVM research: dsh/.agent-writing/plans/2026-10-16-self-hosted-microvm-for-dsh.md
