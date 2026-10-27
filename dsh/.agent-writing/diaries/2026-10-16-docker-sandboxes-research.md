# 2026-10-16 - Docker Sandboxes research and plan

## Why

User read about "Docker Sandbox" providing a sandbox that still has Docker inside, and
asked what changes would be needed for the dsh harness. Deliverable: a plan under
`.agent-writing/plans`.

## What I found

- **Docker Sandboxes (`sbx`)** is Docker's agent-sandboxing product. A local sandbox is a
  microVM (separate kernel) with a **private Docker Engine**; the host daemon is never
  mounted. Network is deny-by-default through a host proxy; credentials can be injected
  host-side so keys never enter the VM.
- **Requirements:** local sandboxes need KVM, officially on **Ubuntu 24.04+** (macOS Apple
  silicon / Windows 11 otherwise). `sbx login` (Docker account) is required even for free
  local compute. Cloud sandboxes avoid local virtualization but are pay-as-you-go.
- **This host is Debian 13 (trixie)**, kernel 6.12, Intel VT-x present. Docker does not
  support Debian for sbx, and `/dev/kvm` cannot be checked from inside this container. That
  is the top feasibility risk.
- **Custom agents** are supported through v3 kits (descriptor + Dockerfile). Base-image
  contract: non-root `agent` user (UID 1000, home `/home/agent`), `/bin/sh` + `/bin/bash`, CA
  certs, launch command. `docker/sandbox-templates:shell` already ships that user, Docker
  CLI, Node, Python, UV and sudo.
- **Workspaces** mount at their host absolute paths (not the current `/workspace/<name>`
  convention); extra dirs via `additionalWorkspaces`. `sbxenv.yaml` environment files
  (experimental) declare agent, workspace, mounts, ports, env, secrets, lifecycle.
- **Ports:** `sbx --publish host:sandbox` / `sbx ports`. A service must listen on **all
  interfaces** to be reachable. `dsh web` deliberately refuses `--host 0.0.0.0` and binds
  `127.0.0.1:3080` (verified in the installed web-app source), so a socat forwarder inside
  the sandbox is mandatory for the UI.
- **Credentials:** prefer `com.docker.sandbox/credential@1` + `sbx secret set` (host-side
  sentinel). Environment variables still work but expose keys inside the VM.

## Decisions

- Plan phases: **Phase 0** host feasibility gate -> **Phase 1** `shell` sandbox PoC
  (Docker, dsh install, forwarder, port publish, persistence) -> **Phase 2A** package dsh as
  a v3 workload kit (recommended target).
- **Option B** (run the existing compose stack inside a `shell` sandbox and mount the
  *in-VM* `/var/run/docker.sock`) is the documented fallback: smallest change, preserves
  the current UI/volumes, but nests containers.
- Start provider auth with environment variables (same trust level as today's compose), then
  migrate used providers to proxy-managed credentials.
- Do not edit any `README.md` (global rule); document the new run mode in
  `.agent-writing/docs/MAIN.md` during implementation.
- Keep the existing compose path as a fallback.

## Open questions

- Does `sbx` run acceptably on Debian 13 via release artifacts, or is Ubuntu/cloud required?
- Is KVM actually usable on the host (module, `/dev/kvm`, `kvm` group, nested virt)?
- Kit build context: the repo `.dockerignore` excludes `global-agent-config`, which the kit
  needs; resolve with a root-level kit and/or a `just` staging recipe.
- Which providers to move to `credential@1` first, and whether dsh provider headers match
  the capability's injection model.

## Artifact

- Plan: `.agent-writing/plans/2026-10-16-docker-sandboxes-for-dsh.md`

## Sources

- https://docs.docker.com/ai/sandboxes/
- https://docs.docker.com/ai/sandboxes/install/
- https://docs.docker.com/ai/sandboxes/architecture/
- https://docs.docker.com/ai/sandboxes/security/
- https://docs.docker.com/ai/sandboxes/customize/author/base-images/
- https://docs.docker.com/ai/sandboxes/configuration/environment-files/
- https://docs.docker.com/ai/sandboxes/configuration/credentials/
- https://docs.docker.com/ai/sandboxes/workflows/development/
- https://docs.docker.com/ai/sandboxes/troubleshooting/
