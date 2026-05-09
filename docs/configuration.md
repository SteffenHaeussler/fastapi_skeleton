# Configuration guide

This service has four configuration surfaces:

- `FASTAPI_ENV` — selects which deployment block from `config.toml` is active
- `config.toml` — checked-in, deployment-shaped defaults
- `.env.example` / `.env` — local env-var template
- `compose.yml` — interpolates env vars when running under Docker Compose

The pydantic settings layer that ties them together lives in `src/app/config.py`.
A separate, smaller path for process-shape knobs lives in `src/app/runtime.py`.

## Source precedence

Configuration has three layers. Higher wins:

1. **Process env vars** (and `.env` files loaded by your shell or Compose)
2. **`config.toml`** — checked-in deployment defaults
3. **Pydantic model defaults** in `src/app/config.py`

This order is enforced by `Config.settings_customise_sources` in
`src/app/config.py:70`, which returns `(env_settings, TomlConfigSettingsSource)`.
Env wins over TOML; both win over field defaults.

## `FASTAPI_ENV`

Selects which `[DEV]` / `[STAGE]` / `[PROD]` / `[TEST]` block of `config.toml`
is exposed via `Config.api_mode` (`src/app/config.py:84`).

- Validated against `VALID_FASTAPI_ENVS` (`src/app/config.py:46`,
  `src/app/config.py:60`); invalid values raise at startup.
- Default: `DEV` (`src/app/config.py:48`).
- Set it in your shell, in `.env`, or in Docker. The Dockerfile's `runtime`
  stage hard-codes `FASTAPI_ENV=PROD` (`Dockerfile:69`) and the `test` stage
  hard-codes `TEST` (`Dockerfile:52`).
- `run_app.sh` also branches on this value to pick uvicorn worker count and
  log level.

Application code should read configuration through `config.api_mode`, not by
reaching into `config.PROD` etc., so logic stays env-agnostic.

## `config.toml`

Loaded by `TomlConfigSettingsSource` (`src/app/config.py:81`); the path is
declared at `src/app/config.py:45`.

Use it for **non-secret, deployment-shaped settings** — values that differ per
environment but are safe to commit.

Schema: a top-level `VERSION` plus four blocks (`DEV`, `STAGE`, `PROD`,
`TEST`). Each block is a `Deployment` model (`src/app/config.py:37`):

- `CONFIG_NAME`, `DEBUG`
- `cors` — `CORSConfig` (`src/app/config.py:14`)
- `observability` — `prometheus`, `tracing` (`src/app/config.py:22`)

Defaults disable the optional features (CORS, Prometheus, tracing). The file
itself shows commented examples you can uncomment to opt in per environment.

**Never put secrets in `config.toml`.** It is committed to the repository.

## `.env.example` and local `.env`

`.env.example` is a committed template. Copy it to `.env` for local use. It
documents the two env vars used in local workflows:

- `FASTAPI_ENV` — `DEV` / `STAGE` / `PROD` / `TEST`
- `PORT` — Compose host-port binding (see below)

Important: pydantic-settings does **not** auto-load `.env` for the `Config`
class. No `env_file` is configured (`src/app/config.py:58`). `.env` is consumed
by **Docker Compose** and by anything you `export` manually in your shell. Do
not assume that adding a key to `.env` will appear in `Config` unless you also
export it into the process environment.

## Compose `.env`

`compose.yml` interpolates `${FASTAPI_ENV:-DEV}` and `${PORT:-5000}`. Compose
reads `.env` from the project root automatically.

- `PORT` only changes the **host-side** port mapping. The container always
  listens on `5000` (`compose.yml:10`, `Dockerfile:70`, `run_app.sh:4`).
- `FASTAPI_ENV` here overrides the Dockerfile's baked-in `PROD` for the
  `runtime` stage.

## Runtime-only env vars (not in `Config`)

`PORT` and `WEB_CONCURRENCY` are read directly in
`src/app/runtime.py:36`, not through pydantic `Config`. They are
process-shape knobs (bind port, uvicorn worker count), not application config.

Defaults baked into the production image: `PORT=5000`, `WEB_CONCURRENCY=2`
(`Dockerfile:70`).

## Where does this setting belong?

| Kind of setting | Lives in | Example |
|---|---|---|
| Secrets, per-deploy URLs / tokens | env vars (orchestrator or secret store; `.env` only for local) | DB password, API key |
| Deployment-shaped feature toggles and lists | `config.toml` block | `cors.allow_origins`, `observability.prometheus.enabled` |
| Hard-coded sensible defaults | pydantic field defaults (`src/app/config.py`) | `PrometheusConfig.path = "/metrics"` |
| Process / runtime knobs | env vars read in `src/app/runtime.py` | `PORT`, `WEB_CONCURRENCY` |
| Which env block to use | `FASTAPI_ENV` | `DEV` locally, `PROD` in the prod image |

Rule of thumb: if it is a secret or differs per deploy, env var. If it shapes
a deployment but is safe to commit, TOML. If it is a code default, model.

## Adding a new setting — checklist

1. Is it a secret? → env var, and document the name in `.env.example`.
2. Is it per-environment but safe to commit? → add a field to a pydantic model
   in `src/app/config.py`, then set it in each block of `config.toml` (or rely
   on the default).
3. Is it a process-shape knob (bind port, worker count, log level)? → add to
   `src/app/runtime.py` and the `Dockerfile`.
4. Update this file so the new knob is discoverable.
