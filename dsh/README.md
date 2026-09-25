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

The container is wired for several model providers at once. DeepSeek's own API
works out of the box through the built-in `deepseek-official` route; Vercel AI
Gateway is seeded through the multi-provider `dsh-llm-pi-ai` adapter.

Put the keys you have in `.env` (see `.env.example`) and run `just recreate`:

```sh
DEEPSEEK_API_KEY=sk-...
AI_GATEWAY_API_KEY=...
```

- Compose auto-loads `.env` for interpolation and passes every variable in it
  into the container (`env_file`), so a new provider key needs no compose edit.
  A blank key counts as unset, so leaving one out is harmless.
- The routes are declared in `global-agent-config/cordis.patch.yml`, mounted
  read-only at `$DSH_HOME/cordis.patch.yml`. It seeds Vercel AI Gateway and
  carries commented entries for the other pi-ai catalog providers (OpenAI,
  Anthropic, Google, OpenRouter, Groq, xAI, ...) and for hand-declared
  OpenAI/Anthropic-compatible endpoints. The file hot-reloads; uncomment a
  route to enable it.
- Choose the model per session from the model selector, or change the default
  from the Web **Models** page.

Adding a provider without editing any file: open the Web **Models** page, add
the provider/route, and (if its key is not already in `.env`) paste the key.
Those edits live in `$DSH_HOME/settings.yaml` and `$DSH_HOME/.credentials.yaml`
on the persistent `dsh-home` volume, merge over `cordis.patch.yml`, and survive
`just recreate` / `just down`.

Notes:

- `web_search` uses `DEEPSEEK_API_KEY` (the harness's shipped search provider),
  so keep a DeepSeek key if you want web search even while chatting through
  another provider.
- Keys are read from the container environment per request, so after editing
  `.env` run `just recreate` to pass the new value in; routes added from the Web
  UI take effect immediately.

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
- **Updating dsh.** It's pinned in `package.json`. Bump the version there, run
  `pnpm install` to refresh `pnpm-lock.yaml`, then rebuild (`just recreate`).

## Hardening

The container is the security boundary: non-root user (uid 1000, matching the host),
read-only rootfs, tmpfs `/tmp`, all capabilities dropped, `no-new-privileges`,
and only explicitly mounted workspace folders. See SAFETY.md — the harness itself
is experimental and un-audited; keep backups of anything the agent can touch.
