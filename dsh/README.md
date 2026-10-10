# my-dsh-container

Runs [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) (`dsh`)
in a container, as recommended by the project's
[SAFETY.md](https://github.com/deepseek-ai/deepseek-harness/blob/master/SAFETY.md).

## Quick start

```sh
cp .env.example .env 
```
Add the API keys you have (at least one model provider — see
[Model providers](#model-providers)).

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

## Model providers

DeepSeek's own API works out of the box through the built-in `deepseek-official`
route. Every other provider (Vercel AI Gateway, OpenAI, Anthropic, Google, ...)
is configured once from the Web **Models** page and stored in the active
profile's `cordis.patch.yml`, so dsh owns that configuration and this repo does
not duplicate it.

Put the keys you have in `.env` (see `.env.example`) and run `just recreate`:

```sh
DEEPSEEK_API_KEY=sk-...
AI_GATEWAY_API_KEY=...
```

- Compose auto-loads `.env` for interpolation and passes every variable in it
  into the container (`env_file`), so a new provider key needs no compose edit.
  A blank key counts as unset, so leaving one out is harmless.
- dsh ships a catalog of providers whose endpoint, protocol, model list, and
  environment-variable name are built in. Adding one from the Models page (for
  example Vercel AI Gateway) therefore reads `AI_GATEWAY_API_KEY` straight from
  the environment: no key to paste and no route file to edit. The catalog covers
  OpenAI, Anthropic, Google, OpenRouter, Groq, xAI, and more.
- Open **Settings → Models → Add model provider**. For an endpoint the catalog
  does not ship (a relay, a self-hosted server, any OpenAI/Anthropic-compatible
  gateway), choose **Custom model API** and fill in the endpoint, protocol, and
  models.
- Choose the model per session from the model selector, or change the default
  from the Web **Models** page.

Provider routes added or edited in the Models page live in the profile patch and
`$DSH_HOME/.credentials.yaml` on the persistent `dsh-home` volume, and survive
`just recreate` / `just down`.

Notes:

- `web_search` uses `DEEPSEEK_API_KEY` (the harness's shipped search provider),
  so keep a DeepSeek key if you want web search even while chatting through
  another provider.
- Keys are read from the container environment per request, so after editing
  `.env` run `just recreate` to pass the new value in; providers added from the
  Web UI take effect immediately.

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

Harness-level skill definitions live at
`global-agent-config/skills/<name>/SKILL.md` and are bind-mounted read-only into
dsh's user skill root:

```yaml
- ./global-agent-config/skills:/dsh-home/skills:ro
```

## Notes

- **Python environments (uv).** `uv` is installed in the image and configured
  with `UV_PROJECT_ENVIRONMENT=.venv-agent-container`, so each project gets its
  environment in a project-local `.venv-agent-container/` directory. The
  container never reads or overwrites the host's `.venv`, and uv no longer
  deletes a `.venv` that was built for the host. `.venv-agent-container` is still
  bound to the container's Python, so recreate one on the host if you work on the
  project directly there. Agent-facing rules live in `global-agent-config/AGENTS.md`.
- **Networking.** `dsh` only binds `127.0.0.1` and refuses `--host 0.0.0.0`, so the
  container uses host networking to be reachable at `localhost:3080`. That means
  the container can also reach other host services on loopback. For stronger
  isolation, bind a static container IP and run `dsh web --host <ip>` instead.
- **Telemetry is disabled** (`DSH_TELEMETRY_MODE=DISABLED`).
- **Package managers.** `dsh` and its dependencies are installed with `pnpm`
  from `package.json` / `pnpm-lock.yaml` during the build. The only thing npm
  installs is `pnpm` itself (`pnpm@12.4.2`, pinned in the `Dockerfile`);
  `dsh plugin` uses that same pnpm at runtime.
- **Native addon cache.** dsh 0.2 loads a native binding at startup and, by
  default, copies the prebuilt `.node` into `/tmp` and maps it executable. The
  container's `/tmp` is `noexec`, so that mapping fails and dsh exits with
  `No usable native binding found`. The `Dockerfile` sets
  `NARB_NATIVE_CACHE_DIR=$DSH_HOME/.cache/native-binaries` to put the copy on
  the executable `dsh-home` volume instead.
- **`$DSH_HOME` is writable by dsh, not by the agent.** The `dsh-home` volume
  holds sessions, credentials, settings, and profile patches, so the harness
  process and the Web UI write it. The agent's file sandbox is narrower: it may
  only write the mounted workspace, which keeps a session from rewriting its own
  harness config. That split is deliberate; a rebuild restores the image and the
  volume carries the user state forward.
- **Updating dsh.** It's pinned in `package.json`. Bump the version there, run
  `pnpm install` to refresh `pnpm-lock.yaml`, then rebuild (`just recreate`).

## Hardening

The container is the security boundary: non-root user (uid 1000, matching the host),
read-only rootfs, tmpfs `/tmp`, all capabilities dropped, `no-new-privileges`,
and only explicitly mounted workspace folders. See SAFETY.md — the harness itself
is experimental and un-audited; keep backups of anything the agent can touch.
