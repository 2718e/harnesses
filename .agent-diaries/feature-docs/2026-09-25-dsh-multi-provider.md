# dsh container: multi-provider model API keys (DeepSeek + Vercel AI Gateway)

Date: 2026-09-25

## Problem

The container hard-coded a single provider: `compose.yaml` passed only
`DEEPSEEK_API_KEY` and dsh offered only the built-in `deepseek-official`
(`dsh-llm-deepseek`) route, so the model picker had one provider's models.

Goal: let any provider's API key be used, with DeepSeek and Vercel AI Gateway
working out of the box and multiple model choices in the picker.

## What dsh already provides

`@deepseek-ai/dsh-base` mounts `@deepseek-ai/dsh-llm-pi-ai` **dormant**: zero
routes and no extra picker models until a `providers` dict is supplied. That
adapter is the generic path. Its `providers` keys are route names, and each
route either

- names an installed **pi-ai catalog provider** (`openai`, `anthropic`,
  `google`, `openrouter`, `deepseek`, `vercel-ai-gateway`, ...) so the endpoint,
  protocol, and model catalog come from pi-ai, or
- **hand-declares** a route with `api`, `baseURL`, and a non-empty `models`
  list for anything pi-ai does not ship (any OpenAI- or Anthropic-compatible
  gateway / self-hosted server).

Credentials are never stored in config. `apiKeyEnv` names an environment
variable, resolved per request through the `dsh-credentials-local` seam
(inherited process env wins, then `$DSH_HOME/.credentials.yaml`, then project /
home `.env`). A blank value is treated as unset.

`@earendil-works/pi-ai@0.85.1` ships a `vercel-ai-gateway` provider:
`baseUrl: https://ai-gateway.vercel.sh`, `anthropic-messages` protocol,
`AI_GATEWAY_API_KEY`, and a 237-model catalog including `deepseek/deepseek-v4-*`.

The pi-ai config can come from either the composition tree (a `cordis.patch.yml`
row) or `$DSH_HOME/settings.yaml` under an `llm-pi-ai:` section (what the Web
Models page writes). Settings merge over composition per provider.

## Changes

- `dsh/compose.yaml`
  - Replaced the single `DEEPSEEK_API_KEY` entry with a pass-through list of the
    common catalog providers' standard env vars (`AI_GATEWAY_API_KEY`,
    `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, ...), each as
    `${VAR:-}` so a blank value means unset.
  - Added `env_file: .env` with `required: false`, so *every* variable in
    `./.env` reaches the container and a new provider needs no compose edit.
  - Bind-mounted `./global-agent-config/cordis.patch.yml` read-only at
    `/dsh-home/cordis.patch.yml`.
- `dsh/global-agent-config/cordis.patch.yml` (new): the home-level patch layer,
  applied to every profile and hot-reloaded. It configures `llm-pi-ai` with the
  `vercel-ai-gateway` route (`apiKeyEnv: AI_GATEWAY_API_KEY`) and carries
  commented entries for the other catalog routes plus a hand-declared gateway
  example.
- `dsh/.env.example`: documents `AI_GATEWAY_API_KEY`, the other catalog keys,
  and that any key in `.env` is passed through.
- `dsh/README.md`: new "Model providers" section; quick start mentions keys.
  Fixed the stale `harness-level-skills/skills` path to
  `global-agent-config/skills`.

DeepSeek needed no new route: the built-in `deepseek-official` route already
covers it (and is what `web_search` uses). Vercel's catalog also serves DeepSeek
models, so a single `AI_GATEWAY_API_KEY` can drive DeepSeek *and* other vendors.

## Verification performed

No Docker on this container, so compose was reviewed rather than executed.
dsh itself was exercised with a scratch `DSH_HOME` (`/tmp/dsh-test-home`) and the
same patch file, using the shipped `@deepseek-ai/dsh` 0.1.5-rc.2:

- `dsh --profile web --dump-config` composed successfully and showed the
  `llm-pi-ai` row with the `vercel-ai-gateway` provider and its `apiKeyEnv`.
- Headless boot with the default model forced to `vercel-ai-gateway` /
  `deepseek/deepseek-v4-pro` and `AI_GATEWAY_API_KEY=dummy` failed with the
  gateway's own `401 authentication_error` — proving the route registered, the
  credential seam resolved the env var, and the request reached
  `https://ai-gateway.vercel.sh`.
- Headless boot with a hand-declared route (`api: openai-completions`,
  `baseURL: http://127.0.0.1:9/v1`, explicit `models`) failed with
  `TRANSPORT: Connection error.` — the profile validated and the route
  registered.

## Notes / gotchas

- `env_file.required` needs Compose >= 2.24. The explicit `environment` list
  covers the common providers independently, so narrowing to a simple
  `- .env` is the fallback on older Compose.
- `env_file` cannot be limited to `*_API_KEY`, so every `.env` variable enters
  the container; keep unrelated secrets out of `dsh/.env`.
- Composition routes cannot be deleted by `settings.yaml` (the user layer only
  adds/overrides), so a route seeded in `cordis.patch.yml` stays visible even if
  its key is unset; requests for it fail with `MISSING_CREDENTIAL`.
- The home patch replaces the targeted row's whole `config`; if a future dsh
  version ships default providers in the base `llm-pi-ai` row, this file would
  need to restate them.
- The seed enables only Vercel AI Gateway by default to keep the picker free of
  keyless providers. Other catalog routes are one uncommented line away, or can
  be added from the Web Models page without a rebuild.
- `web_search` remains DeepSeek-backed (`DEEPSEEK_API_KEY`), independent of the
  chat provider.

## Not implemented: env-driven default model

An env seam for the default provider/model (`DSH_DEFAULT_PROVIDER` /
`DSH_DEFAULT_MODEL`) was prototyped and then removed. A composition patch cannot
drive it, because dsh layers the `agent-default-model` user settings section
over the composition default, and the Web session controller saves a selection
on every model pick. The prototype worked around that by rewriting
`$DSH_HOME/settings.yaml` from a container entrypoint; that was rejected as too
hacky. See the chat/PR discussion for cleaner options under investigation.
