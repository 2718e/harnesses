# VM environment

You are running inside a Lima VM, not on the host. The host filesystem is visible only through the mounted paths below. There are no host SSH keys and no host credentials.

## Mounts

- /projects/<name> - project checkouts. Some are writable and some are read-only; check the mount before editing.
- /datasets - read-only reference data.
- /new-projects - writable staging area for new projects.
- /opt/agent-config - read-only harness configuration; do not edit.

## Privileges

- There is no sudo. Do not run sudo, apt, system-wide systemctl, or commands that assume root.
- System packages are part of the VM image. If you need one, report it; the host must add it to provisioning and recreate the VM.
- User-local installs are fine: uv, pnpm/npm with the user prefix, rustup, project dependencies.

## Containers

- Use rootless Docker and Docker Compose: docker run, docker build, docker compose.
- The Docker daemon runs as the VM user; the system Docker socket is disabled.

## Languages

- Python: use uv. The project environment is .venv-agent-container, so the host .venv is never touched.
- Node: use pnpm. Global installs go under ~/.local.
- Tools available: rg, fd, ast-grep (sg), tree-sitter, jq, uv, pnpm.
- tree-sitter grammars may need to be fetched per project.

## Git

- Git works locally: branches, commits, worktrees.
- There are no remote credentials. Public clones work, pushes do not. The host can recover from the remote.
- Do not put secrets in the repository.

## Harnesses

- Codex and dsh are available as commands in the VM shell.
- Do not write into read-only mounts or use tricks to bypass mount permissions.
