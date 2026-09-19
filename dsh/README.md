# my-dsh-container

Runs [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) (`dsh`)
in a container, as recommended by the project's
[SAFETY.md](https://github.com/deepseek-ai/deepseek-harness/blob/master/SAFETY.md).

## Quick start

```sh
cp .env.example .env 
```
Add the DEEPSEEK_API_KEY to .env

Then, with [`just`](https://just.systems) installed on the host:

```sh
just start    # build if needed, start, and print the URL with the token
```

Run `just` on its own to list all recipes (`url`, `recreate`, `logs`, `shell`,
`stop`, `down`, ...). Open the printed URL in the browser.
Note that the workspace is the level above the default folder

The underlying commands still work if you prefer not to use `just`:

```sh
docker compose up -d --build
docker compose logs # to see the url with the token
```

## Adding a project

Projects are mounted individually so the container only sees what you give it.

The main compose file includes a gitignored `compose.folders.yaml` which can be used to
add project folders, resource folders, etc/

`compose.folders.example.yaml` gives an example of adding this repository itself.

```sh
just recreate
```

Then pick the new mount path in **Choose workspace**.

## Skills

Harness-level skill definitions live defined at
`harness-level-skills/skills/<name>/SKILL.md` and are bind-mounted read-only into
dsh's user skill root:

```yaml
- ./harness-level-skills/skills:/dsh-home/skills:ro
```

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
