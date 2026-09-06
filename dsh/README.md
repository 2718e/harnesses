# my-dsh-container

Runs [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) (`dsh`)
in a container, as recommended by the project's
[SAFETY.md](https://github.com/deepseek-ai/deepseek-harness/blob/master/SAFETY.md).

## Quick start

```sh
cp .env.example .env        # add your DEEPSEEK_API_KEY
docker compose up -d --build
```

Open http://localhost:3080 in a browser. In **Settings → Models** add your DeepSeek
API key, then **Choose workspace** and select `/workspace` (the mounted project).

## Adding a project

Projects are mounted individually so the container only sees what you give it.
Add a line under `volumes` in `compose.yaml` and recreate the container:

```yaml
volumes:
  - path-to-this-project:/workspace
  - this-projects-parent-folder/individual-project:/individual-project
```

```sh
docker compose up -d --force-recreate
```

Then pick the new mount path in **Choose workspace**.

## Notes

- **venvs are container-scoped.** A virtualenv the agent creates inside a project
  is bound to the container's Python at `/usr/local/bin`. It works for the agent,
  but that project's Python tooling on the host won't reuse it — recreate a venv
  there if you work on the project directly on the host.
- **Networking.** `dsh` only binds `127.0.0.1` and refuses `--host 0.0.0.0`, so the
  container uses host networking to be reachable at `localhost:3080`. That means
  the container can also reach other host services on loopback. For stronger
  isolation, bind a static container IP and run `dsh web --host <ip>` instead.
- **Telemetry is disabled** (`DSH_TELEMETRY_MODE=DISABLED`).
- **Updating dsh.** It's pinned in the `Dockerfile`; bump the version there and
  `docker compose build` to update.

## Hardening

The container is the security boundary: non-root user (uid 1000, matching the host),
read-only rootfs, tmpfs `/tmp`, all capabilities dropped, `no-new-privileges`,
and only explicitly mounted workspace folders. See SAFETY.md — the harness itself
is experimental and un-audited; keep backups of anything the agent can touch.
