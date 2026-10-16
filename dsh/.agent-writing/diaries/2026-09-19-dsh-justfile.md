# dsh justfile

Date: 2026-09-19

## What

Added `dsh/justfile` wrapping the common `docker compose` invocations for the
dsh container, so the workflow is `just start` / `just recreate` instead of
typing compose commands and digging the authenticated URL out of the logs.

## Recipes

| Recipe | Effect |
| --- | --- |
| `just build` | `docker compose build` |
| `just start` | `docker compose up -d`, then print the web URL |
| `just recreate` | `docker compose up -d --build --force-recreate`, then print the URL |
| `just url` | Wait up to 60s for the startup line and print the URL with its token |
| `just logs` | `docker compose logs -f` |
| `just shell` | `docker compose exec dsh bash` |
| `just stop` | `docker compose stop` |
| `just down` | `docker compose down` (keeps the `dsh-home` volume) |

`just` (no recipe) lists them all.

## How the URL is detected

`dsh-web-app` logs one line at startup:

```
dsh web: http://localhost:3080/?token=<launch-token> (LAN: ...)
```

The `url` recipe polls `docker compose logs dsh` and extracts the first URL with
`sed -n 's/.*dsh web: \(http[^ ]*\).*/\1/p' | tail -n1`, so the LAN variant is
ignored and the newest process's token wins. On a fresh home the first boot can
take a while, hence the 60s wait.

## Notes / gotchas

- The justfile lives in `dsh/` because `just` runs recipes from the justfile's
  directory, and compose then picks up `./compose.yaml` (plus its `include:` of
  `compose.folders.yaml`) and `./.env` without extra flags.
- `just` passes `$` through to the shell verbatim; `$$` is *not* an escape (it
  expands to the shell PID). The recipes use single `$`.
- Prerequisite on the host: `just` plus Docker Compose. Neither is installed in
  the image.
