# Plan: Docker Sandboxes for the dsh harness

- **Date:** 2026-10-16
- **Status:** Proposed — research complete, implementation not started
- **Project:** `harnesses/dsh` (the container this session runs in)
- **Goal:** give the dsh agent real Docker (build/run/Compose) without exposing the host Docker daemon, by adopting Docker Sandboxes (`sbx`).
- **Related:** the self-hosted microVM plan (`2026-10-16-self-hosted-microvm-for-dsh.md`) is the alternative to this one.

## TL;DR

- Docker Sandboxes already *is* the requested capability: each local sandbox is a microVM
  with its **own private Docker Engine**. Nothing from the host daemon is mounted.
- dsh is not a supported `sbx` agent, but `sbx` v3 **kits** support custom workloads, so dsh
  can be packaged as one.
- Two blockers are host-side, not code:
  1. Local sandboxes need **KVM on Ubuntu 24.04+**; this host is **Debian 13**, which Docker
     does not support or test. This is the first thing to check.
  2. `sbx` requires a **Docker account** (`sbx login`) even for free local sandboxes.
- One confirmed integration quirk needs code: `sbx` publishes a port only if the service
  listens on **all interfaces**, but `dsh web` deliberately refuses `--host 0.0.0.0`.
  A tiny in-sandbox TCP forwarder (socat) on a second port solves it.
- **Recommendation:** Phase 0 host gate -> Phase 1 `shell` sandbox proof-of-concept ->
  Phase 2 package dsh as a v3 workload kit. Keep the current hardened compose container
  as the fallback and for comparison.

## 1. What Docker Sandboxes is

`sbx` is Docker's agent-sandboxing product. A local sandbox is a lightweight microVM
(separate kernel) with:

- full agent privileges inside: `sudo`, package installs, and a **private Docker Engine**;
- deny-by-default outbound network through a host proxy (allow-list per sandbox);
- host-side credential injection so API keys never enter the VM;
- workspace sharing by direct mount / clone / mountless;
- published ports (`--publish host:sandbox`), SSH access (`ssh <name>.sbx`), `sbx exec`.

It is explicitly positioned as the alternative to "container + host Docker socket":

| Approach | Isolation | Docker access |
| --- | --- | --- |
| Docker Sandboxes | full (hypervisor) | isolated per-sandbox daemon |
| Container + socket mount | partial (namespaces) | shared host daemon |
| Docker-in-Docker | partial (privileged) | nested daemon |
| Host execution | none | host daemon |

Custom agents are packaged as **v3 kits**: a YAML descriptor (`kind: workload`) plus a
Dockerfile. Base-image requirements are a non-root `agent` user (UID 1000, home
`/home/agent`), `/bin/sh` + `/bin/bash`, CA certs, and a launch command. Docker's
`docker/sandbox-templates:shell` image already provides that user, Docker CLI, Node,
Python, UV and sudo on Ubuntu.

An **environment file** (`sbxenv.yaml`) declares the agent/kit, workspace,
`additionalWorkspaces`, `ports`, `env`, `secrets`, `lifecycle` and `sandboxOptions`, so
the whole setup can be committed and reproduced with `sbx env run`.

## 2. Current setup (baseline)

- `Dockerfile`: Debian `python:3.13-slim` + Node 24.13 + `uv` + `pnpm` + pinned
  `@deepseek-ai/dsh@0.2.0-rc.2`, non-root `dev` (uid/gid 1000), `DSH_HOME=/dsh-home`.
- `compose.yaml`: `network_mode: host`, `read_only`, `tmpfs /tmp`, `cap_drop: ALL`,
  `no-new-privileges`, named `dsh-home` volume, read-only skills + `AGENTS.md` mounts.
- `compose.folders.yaml` (gitignored): host projects mounted read-write under
  `/workspace/<name>` plus one read-only data dir.
- `justfile`: `start`, `recreate`, `url`, `logs`, `shell`, `stop`, `down`.
- CMD: `dsh web --no-open --trusted-host localhost --trusted-host 127.0.0.1`.
- The agent currently has **no Docker**, and the dsh file sandbox only lets it write the
  workspace (this session was denied a write to `/dsh-home`).

## 3. Gap analysis

| Concern | Today (compose) | With Docker Sandboxes | Change required |
| --- | --- | --- | --- |
| Isolation | container namespaces | microVM + hypervisor | none (stronger) |
| Docker for agent | none | private engine, native `docker` | none (the point) |
| Host OS support | any Docker host | Ubuntu 24.04+/KVM (local), or cloud | **verify/gate** |
| Auth | API keys in env | `sbx login` + `sbx secret` or env | add account + secrets |
| Agent packaging | Dockerfile image | built-in agents only | **author a v3 workload kit** |
| Web UI | host networking, `localhost:3080` | port publish, all-interfaces rule | **socat forwarder + publish** |
| Provider keys | `.env` -> container env | proxy-injected sentinel (preferred) or env | start with env, migrate later |
| Mounts | renamed paths under `/workspace` | same absolute host paths + `additionalWorkspaces` | remap `compose.folders.yaml` |
| Persistent state | `dsh-home` volume | inside the VM, lost on `sbx rm` | optional host mount |
| Skills / `AGENTS.md` | read-only bind mounts | baked into image or `agent-context` | bake/copy into kit |
| Hardening | read-only rootfs, caps dropped | agent has sudo inside VM | document the shift |

## 4. Phase 0 — host feasibility gate (run on the host, not in this container)

These commands are for the host (`danscomputer`), not for the dsh session:

```sh
uname -r
grep -Eo 'vmx|svm' /proc/cpuinfo | head -1        # CPU virtualization present
lsmod | grep -E 'kvm_(intel|amd)|kvm_arm64'        # KVM module loaded
ls -l /dev/kvm                                     # KVM device present
kvm-ok 2>/dev/null || true                         # cpu-checker, if installed
groups | tr ' ' '\n' | grep -x kvm                 # user in kvm group
```

Then install and diagnose `sbx` (Ubuntu path; Debian is unsupported):

```sh
curl -fsSL https://get.docker.com | sudo SBX=1 sh  # or: sudo apt install docker-sbx
sbx login
sbx diagnose --format github-issue
sbx --version
```

**Decision gate.** Local sandboxes only if KVM works *and* you accept running an unsupported
`sbx` build on Debian (release artifacts). Otherwise pick: (a) install/dual-boot Ubuntu
24.04 for reliable local sandboxes, or (b) use `sbx --cloud` (no KVM, pay-as-you-go, but
workspace/ports/expiration behave differently). Do not proceed to Phase 2 before this gate
passes on the intended host.

## 5. Architecture options

**Option A — package dsh as a v3 workload kit (recommended target).**
dsh runs directly in the microVM as `agent`; the agent gets the VM's Docker engine natively.
No nested containers. Cost: author and maintain a kit; handle the web-server launch and port
forwarding.

**Option B — run the existing compose stack inside a `shell` sandbox (bridge/fallback).**
Keep the current `Dockerfile`/`compose.yaml`; add the Docker CLI + Compose to the image and
mount the **in-VM** `/var/run/docker.sock` into the dsh container. The agent then drives the
sandbox's isolated engine (Docker-out-of-Docker). Smallest change and preserves the current
UI/volumes, but nests containers and doubles resource overhead.

**Option C — cloud sandboxes.** No local KVM needed; useful only if Phase 0 fails and you
want to pay for compute. Several local features (workspace mounts, ports in the same form)
differ.

Recommendation: **Phase 1 PoC -> Option A**, with Option B as a documented fallback if the
kit launch/UI integration proves awkward.

## 6. Phase 1 — de-risk with a `shell` sandbox (no kit yet)

This validates every risky unknown before writing a kit: Docker-in-sandbox, the dsh native
binding, the forwarder + published port, credentials, and persistence.

```sh
# host, from the harnesses repo
sbx create --name dsh-poc --publish 3080:3081 shell .   # sandbox:3081 -> host:3080
sbx run --name dsh-poc                                   # or: sbx exec -it dsh-poc bash
```

Inside the sandbox:

```sh
node --version && python3 --version && docker --version
docker run --rm hello-world                    # proves the private engine + registry egress
sudo apt-get update && sudo apt-get install -y socat
npm i -g pnpm@12.4.2
pnpm add -g @deepseek-ai/dsh@0.2.0-rc.2        # or use the pinned version from package.json
export DSH_HOME=$HOME/.dsh
export NARB_NATIVE_CACHE_DIR=$HOME/.cache/native-binaries   # only if the addon mmap fails
nohup socat TCP-LISTEN:3081,fork,reuseaddr TCP:127.0.0.1:3080 >/tmp/socat.log 2>&1 &
dsh web --no-open --trusted-host localhost --trusted-host 127.0.0.1
```

Checklist / pass criteria:
- `docker run hello-world` works as `agent` without `sudo` (else the socket group needs fixing).
- If image pulls fail: `sbx policy log`, then `sbx policy allow network "registry-1.docker.io,auth.docker.io"`.
- `dsh web` starts and the browser at `http://localhost:3080` shows the UI with a valid token.
- Provider calls work (start by exporting keys, e.g. `DEEPSEEK_API_KEY`), including `web_search`.
- `sbx exec dsh-poc bash -c "grep 'dsh web:' /tmp/dsh-web.log | tail -1"` gives the URL/token (redirect dsh output to a file in the real entrypoint).
- Stop/start preserves state: `sbx stop dsh-poc && sbx run -d --name dsh-poc` then re-check.

If any step fails, capture `sbx diagnose` output and fall back to Option B or cloud.

## 7. Phase 2A — package dsh as a v3 workload kit

Proposed layout (keep the kit at the project root so the build context can include
`package.json`, `pnpm-lock.yaml`, and `global-agent-config/`):

```text
dsh/
  sbx-kit.yaml            # v3 descriptor, kind: workload
  sbx-kit.dockerfile      # build recipe
  sbx-kit/
    entrypoint.sh         # forwarder + dsh launch
    context.md            # extra agent instructions
  sbxenv.yaml             # environment file (agent, workspace, mounts, ports, env)
```

`sbx-kit.dockerfile` sketch:

```dockerfile
FROM docker/sandbox-templates:shell

USER root
RUN apt-get update && apt-get install -y --no-install-recommends socat \
    && rm -rf /var/lib/apt/lists/*
# Base already has Node/Python/Docker CLI; add uv only if missing.
COPY --from=ghcr.io/astral-sh/uv:0.12.17 /uv /uvx /usr/local/bin/

USER agent
ENV DSH_HOME=/home/agent/.dsh \
    NARB_NATIVE_CACHE_DIR=/home/agent/.cache/native-binaries \
    DSH_TELEMETRY_MODE=DISABLED \
    UV_PROJECT_ENVIRONMENT=.venv-agent-container \
    UV_LINK_MODE=copy \
    BASH_ENV=/etc/sandbox-persistent.sh
ARG DSH_VERSION
RUN npm install -g pnpm@12.4.2 \
    && pnpm add -g @deepseek-ai/dsh@$DSH_VERSION
# Skills + global instructions from the repo, read-only in the image.
COPY global-agent-config/ /home/agent/.dsh/
# Launch dsh through the --expose-internals wrapper, as the compose image does.
COPY sbx-kit/entrypoint.sh /home/agent/bin/dsh-sbx-entrypoint
WORKDIR /home/agent/workspace
ENTRYPOINT ["/home/agent/bin/dsh-sbx-entrypoint"]
CMD []
```

`sbx-kit/entrypoint.sh`:

```sh
#!/bin/sh
# sbx publishes a port only if the service listens on all interfaces; dsh web
# refuses 0.0.0.0, so forward 0.0.0.0:3081 -> 127.0.0.1:3080.
socat TCP-LISTEN:3081,fork,reuseaddr TCP:127.0.0.1:3080 &
exec dsh web --no-open --trusted-host localhost --trusted-host 127.0.0.1 \
  2>&1 | tee /home/agent/dsh-web.log
```

(Use a `dsh-prod` wrapper on `PATH` that runs `node --expose-internals .../bin.js`, matching
the compose image; pin the exact global bin path during implementation.)

`sbx-kit.yaml` sketch:

```yaml
# syntax=docker/sandbox-kit:3
schemaVersion: "3"
kind: workload
displayName: DeepSeek Harness
description: dsh web with a private Docker engine and repo agent config

args:
  version:
    default: "0.2.0-rc.2"
    buildArg: DSH_VERSION

capabilities:
  - type: com.docker.sandbox/sbx@1
  - type: com.docker.sandbox/network-policy@1
    config:
      runtime:
        allow:
          - api.deepseek.com
          - "*.deepseek.com"
          - api.openai.com
          - api.anthropic.com
          - registry.npmjs.org
          - pypi.org
          - files.pythonhosted.org
          - github.com
          - objects.githubusercontent.com
  - type: com.docker.sandbox/agent-context@1
    config:
      filename: AGENTS.md
      content: |
        dsh runs inside a Docker Sandbox with a private Docker engine.
        Use docker/compose directly; never look for a host daemon.
```

Provider credentials are a follow-up: add a `com.docker.sandbox/credential@1` capability per
provider and store the key with `sbx secret set`, so the value never enters the VM. Until
then, pass keys as environment variables (see below) — the same trust level as the current
compose setup.

`sbxenv.yaml` sketch (keep it outside every mounted workspace):

```yaml
schemaVersion: "1"
name: dsh
agent: sbx-kit          # must match the workload's kit name
workspace: ..           # the harnesses repo (mounted at its host absolute path)
additionalWorkspaces:
  - path: /media/dan/data/dev/xr-super
  - path: /media/dan/data/dev/personal-history-mine-v2
  # ... port of compose.folders.yaml; readOnly: true for datasets
ports:
  - sandbox: 3081       # the socat listener; maps to host 3080
    host: 3080
env:
  DEEPSEEK_API_KEY: ... # values entered here are readable inside the VM
```

Note: `sbx` mounts workspaces at their **host absolute paths**, not the current
`/workspace/<name>` convention. Update `global-agent-config/AGENTS.md` and any docs that
assume `/workspace/...`.

Open decision: the repo's existing `.dockerignore` excludes `global-agent-config`. The kit
build needs it, so either drop that exclusion (harmless: the compose image only `COPY`s
`package.json`/`pnpm-lock.yaml`) or stage the files into the kit with a `just` recipe.

## 8. Phase 2B — Option B bridge (fallback)

- `dsh/Dockerfile`: add `docker-ce-cli`, `docker-compose-plugin`, `socat`.
- New `dsh/compose.sbx.yaml` override: `volumes: ["/var/run/docker.sock:/var/run/docker.sock"]`.
- In the sandbox: `cd <repo>/dsh && docker compose -f compose.yaml -f compose.sbx.yaml up -d`.
- Start `socat TCP-LISTEN:3081,fork,reuseaddr TCP:127.0.0.1:3080` on the **VM** (the dsh
  container uses `network_mode: host`, so it owns the VM's `127.0.0.1:3080`). Publish
  `3080:3081`.
- `compose.folders.yaml` still works inside the VM, but its paths are VM-relative and the
  host mounts must first be given to the sandbox via `additionalWorkspaces`.

## 9. Justfile / workflow integration

Add sbx recipes to `dsh/justfile` (keep the compose ones as the fallback path):

- `sbx-start`: `sbx env create` / `sbx run -d --name dsh`
- `sbx-url`: `sbx exec dsh bash -c "grep -o 'http[^ ]*' /home/agent/dsh-web.log | tail -1"`
- `sbx-shell`: `sbx exec -it dsh bash`
- `sbx-status`: `sbx ls`, `sbx ports dsh`
- `sbx-stop` / `sbx-remove`: `sbx stop dsh` / `sbx rm dsh`

Document the new run mode in `dsh/.agent-writing/docs/MAIN.md` (the repo forbids editing
`README.md`).

## 10. Security implications

- The host boundary **improves** (hypervisor vs namespaces), but the in-VM boundary
  **loosens**: the agent gets `sudo` and Docker inside a writable VM, versus today's
  read-only rootfs, dropped capabilities, and no Docker.
- A direct-mounted workspace is read-write; sbx itself warns that Git hooks, CI config, and
  build files are executable content the host may later run. Keep using git and review
  `git diff` plus `.git/hooks`.
- Prefer `--clone` for untrusted work; use direct mount only for the directories the agent
  actually needs.
- Credentials: environment variables (`env:` / `-e`) expose keys inside the VM; the
  proxy-managed `credential@1` + `sbx secret set` route keeps them on the host. Migrate to
  the latter for the providers actually used.
- Do not mount the host Docker socket into anything; the whole point is the private engine.

## 11. Risks and open questions

| Risk / question | Impact | Mitigation |
| --- | --- | --- |
| Debian 13 not supported by `sbx` | local sandboxes may not run | Phase 0 gate; release artifacts, Ubuntu 24.04, or cloud |
| KVM/nested virtualization unavailable | no local microVM | check `/dev/kvm`; use cloud |
| Docker account required (`sbx login`) | headless/automation friction | `sbx login`; see headless docs |
| `dsh web` bound to loopback only | UI unreachable via published port | socat forwarder on 3081 (confirmed need) |
| `sbx --publish` reaches only all-interface listeners | same as above | same |
| Kit build context excludes repo config | skills/AGENTS.md missing | root-level kit + adjust `.dockerignore` |
| Registry/DNS pulls blocked by network policy | `docker run`/`pnpm` fail | `sbx policy allow network`, check `sbx policy log` |
| Provider auth header injection | per-provider `credential@1` work | start with env vars, then add capabilities |
| dsh native addon mmap under noexec paths | dsh fails at boot | `NARB_NATIVE_CACHE_DIR` on a writable exec path |
| State loss on `sbx rm` | sessions/credentials gone | stop/start persists; optional host-dir `DSH_HOME` mount |
| `sbxenv.yaml` is experimental | format may change | pin `sbx` version; plan for migration |

## 12. Verification

- Phase 0: `sbx diagnose` passes; `sbx run shell` reaches a shell.
- Phase 1: checklist in section 6 all pass.
- Phase 2: from a clean clone, `just sbx-start` yields a working UI, `docker run hello-world`
  works from a dsh shell, `git diff` on a mounted repo shows agent edits on the host, and
  `sbx stop`/`sbx run -d` preserves installed packages and images.

## 13. Effort estimate

| Phase | Work | Rough size |
| --- | --- | --- |
| 0 | host checks, install, login, diagnose | hours (blocked on support) |
| 1 | shell PoC + forwarder + creds | half a day |
| 2A | kit + env file + just recipes + docs | 1-2 days |
| 2B | bridge override + docker CLI | half a day (fallback) |
| 3 | credential capabilities, hardening notes | 1 day (follow-up) |

## Sources

- [Docker Sandboxes overview](https://docs.docker.com/ai/sandboxes/)
- [Install Docker Sandboxes](https://docs.docker.com/ai/sandboxes/install/)
- [Architecture](https://docs.docker.com/ai/sandboxes/architecture/)
- [Security model](https://docs.docker.com/ai/sandboxes/security/)
- [Default security posture](https://docs.docker.com/ai/sandboxes/security/defaults/)
- [Build an agent workload](https://docs.docker.com/ai/sandboxes/customize/author/build-an-agent/)
- [Base images for sandbox workloads](https://docs.docker.com/ai/sandboxes/customize/author/base-images/)
- [Sandbox environment files](https://docs.docker.com/ai/sandboxes/configuration/environment-files/)
- [Manage credentials](https://docs.docker.com/ai/sandboxes/configuration/credentials/)
- [Develop and test locally (ports)](https://docs.docker.com/ai/sandboxes/workflows/development/)
- [Troubleshooting](https://docs.docker.com/ai/sandboxes/troubleshooting/)
