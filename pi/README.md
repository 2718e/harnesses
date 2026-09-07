# my-pi-container

Runs the [Pi Agent Harness](https://github.com/earendil-works/pi)
(`@earendil-works/pi-coding-agent`, the interactive `pi` coding agent) in a
container. Pi has no built-in guardrails or permission system, so the container
is the security boundary — the same approach as the dsh setup this was copied
from.

## Quick start

```sh
cp .env.example .env        # add your DEEPSEEK_API_KEY
docker compose up -d --build
docker compose exec -it pi pi
```

Inside `pi` press `Ctrl+L` and pick a model (e.g. DeepSeek → `deepseek-v4-flash`),
then start talking. Mounted projects appear under `/workspace` — `cd` into one
(e.g. `/workspace/harnesses`) before starting a task.

One-off (non-interactive) sessions work too:

```sh
docker compose exec pi pi -p "Summarize what's in /workspace/harnesses"
```

## Plain shell / debugging (no harness)

The container never starts Pi by itself — it idles until you exec something into
it — so opening a plain command line is always available:

```sh
docker compose up -d            # if not already running
docker compose exec -it pi bash
```

You land in a normal `bash` as user `dev`, with Pi on the `PATH`, the API key in
the environment, and the same mounts as a harness session. Poke around, then
start the harness manually from inside whenever you want:

```sh
whoami && pwd                    # dev, /workspace
env | grep -E '^(DEEPSEEK|PI_)'  # key + Pi env vars present?
ls /workspace                    # mounted projects
pi                               # start the harness from this shell
```

Notes:

- Pi is only ever started by you — `up -d` alone runs no harness.
- The root filesystem is read-only by design; only `/workspace`, `/pi-home` and
  `/tmp` are writable, so `touch /etc/test` fails as intended.
- The shell shares the `pi-home` volume with harness sessions, so settings and
  session state are consistent between the two.
- Prefer `exec` while the container is up. For a throwaway shell in a *separate*
  container (same image/config, removed on exit): `docker compose run --rm -it
  pi bash`.

## Extensions

Extensions are declared as ordinary npm dependencies in `package.json` (so
`npm ci` puts them in `/app/node_modules` during the build) **and** registered
in the seeded global settings file (`home/.pi/agent/settings.json`, live at
`/pi-home/.pi/agent/settings.json`) by their `/app/node_modules/<name>` path.
Pi only loads packages that are listed there — it does not auto-discover
extensions from node_modules — and a path entry needs no network access at
session start (unlike `pi install npm:...`, which downloads a second copy into
`/pi-home/.pi/agent/npm` and is versioned independently of the image). After
adding a dependency to `package.json`, rebuild the image (`docker compose
build`) so the new `/app/node_modules/<name>` exists; a plain
`--force-recreate` only swaps the container, not the image.

### Web search

Web search is provided by the [`pi-web-access`](https://github.com/nicobailon/pi-web-access)
extension, which registers a `web_search` tool (plus URL fetching, GitHub clone,
PDF/YouTube extraction, …).

Out of the box it works keyless (it falls back through its provider chain);
results improve when you configure a provider key. Add keys inside the
container — the file lives on the `pi-home` volume, so it survives restarts:

```sh
docker compose exec -i pi tee ~/.pi/web-search.json > /dev/null <<'EOF'
{
  "exaApiKey": "exa-...",
  "tavilyApiKey": "tvly-...",
  "braveApiKey": "BSA_..."
}
EOF
```

Then restart the session (`/reload` in pi, or exit and start a new one). See the
extension's README for the full list of supported providers and keys. Note the
extension runs arbitrary code and can make network requests — this is why Pi
runs in this container.

### Git worktrees

Git worktrees (`/worktree`, `/worktree-exit`, `/worktree-list`,
`/worktree-remove`) are provided by the
[`pi-worktree-extension`](https://github.com/AjayPoshak/pi-worktree-extension)
package. Note: it only works once the current session has been persisted to
disk, which pi does after the first completed assistant turn — send one normal
message and wait for the reply before running `/worktree` in a brand-new
session.

## Adding a project (read-write)

Projects are mounted individually so the container only sees what you give it.
Add a line under `volumes` in `compose.yaml` and recreate:

```yaml
volumes:
  - /path/to/project:/workspace/project
```

```sh
docker compose up -d --force-recreate
```

## Adding a project or resource folder

Projects are mounted individually so the container only sees what you give it.

The main compose file includes a gitignored `compose.folders.yaml` which can be used to
add project folders, resource folders, etc/

`compose.folders.example.yaml` gives an example of adding this repository itself.

Changing mounts requires a container recreate (`up -d --force-recreate`).

## Notes

- **Everything installs via npm.** The harness and plugins are pinned in
  `package.json` / `package-lock.json` and installed with `npm ci` during the
  Docker build. To update Pi or a plugin, bump the version in `package.json`,
  regenerate the lockfile (`npm install --package-lock-only`), and
  `docker compose build`. Nothing harness-specific is installed directly in the
  Dockerfile.
- **State lives on the `pi-home` volume.** Settings, sessions, and packages
  installed with `pi install` persist across recreates (mapped to `/pi-home`,
  seeded from the image on first start).
- **Security posture.** Non-root user (uid 1000, matching the host), read-only
  rootfs, tmpfs `/tmp`, all capabilities dropped, `no-new-privileges`, only
  explicitly mounted folders — plus `:ro` mounts for data. Pi itself is
  un-audited and runs without permission prompts; keep backups of anything the
  agent can touch.
- **No host networking needed.** Pi is a terminal agent and binds no ports
  (unlike dsh's web UI), so the container uses normal bridge networking.
- **Telemetry/update checks disabled** (`PI_SKIP_VERSION_CHECK=1`,
  `PI_TELEMETRY=0`).
- **Python + Node are both available** (python 3.13 base with Node 24), so the
  agent can run Python or JS tooling inside the container.

## Hardening

Read [Pi's security doc](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/security.md)
and containerization guide for the upstream view on running Pi sandboxed.
