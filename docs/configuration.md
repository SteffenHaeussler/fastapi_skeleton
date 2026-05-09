# Configuration guide

This service has four configuration surfaces:

| Surface | Use for |
| --- | --- |
| `FASTAPI_ENV` | Selects the active deployment block from `config.toml` |
| `config.toml` | Checked-in, non-secret deployment defaults |
| `.env.example` / `.env` | Local env-var template and local overrides |
| `compose.yml` | Docker Compose interpolation for local containers |

The pydantic settings layer is in `src/app/config.py`. Process-shape runtime
knobs live in `src/app/runtime.py`.

## Source precedence

Higher wins:

1. Process env vars, including values exported by your shell or injected by
   Compose.
2. `config.toml` deployment defaults.
3. Pydantic model defaults in `src/app/config.py`.

`Config.settings_customise_sources` enforces this order by loading env settings
before `TomlConfigSettingsSource`.

## Setting surfaces

| Setting | Notes |
| --- | --- |
| `FASTAPI_ENV` | Valid values normalize to `DEV`, `STAGE`, `PROD`, or `TEST`. Defaults to `DEV`. Docker runtime defaults to `PROD`; Docker test stage defaults to `TEST`; Compose overrides to `${FASTAPI_ENV:-DEV}` for local use. |
| `config.toml` | Contains top-level `VERSION` plus `[DEV]`, `[STAGE]`, `[PROD]`, and `[TEST]` blocks. Each block maps to the `Deployment` model in `src/app/config.py`. Use it only for non-secret values safe to commit. |
| `.env.example` / `.env` | `.env.example` documents local env vars. Copy it to `.env` for local Compose use. Pydantic `Config` does not auto-load `.env`; values must reach the process environment to affect application config. |
| Compose `.env` | Compose reads project-root `.env` automatically and interpolates `${FASTAPI_ENV:-DEV}` and `${PORT:-5000}`. `PORT` changes only the host-side mapping; the container still listens on `5000`. |
| Runtime-only env vars | `PORT` and `WEB_CONCURRENCY` are read by `src/app/runtime.py`, not pydantic `Config`. They control bind port and uvicorn workers. Docker defaults: `PORT=5000`, `WEB_CONCURRENCY=2`. |

Application code should use `config.api_mode`, not direct access to
environment-specific blocks such as `config.PROD`.

## Where settings belong

| Kind of setting | Lives in | Example |
| --- | --- | --- |
| Secret or per-deploy credential | Env var or secret store | DB password, API key |
| Safe deployment-shaped toggle/list | `config.toml` block | `cors.allow_origins`, `observability.prometheus.enabled` |
| Hard-coded default | Pydantic model default | `PrometheusConfig.path = "/metrics"` |
| Process/runtime knob | Env var read in `src/app/runtime.py` | `PORT`, `WEB_CONCURRENCY` |
| Active deployment selector | `FASTAPI_ENV` | `DEV` locally, `PROD` in image |

Rule of thumb: secrets and deploy-specific values are env vars; safe
per-environment defaults are TOML; code defaults stay in models.

## Adding a setting

1. If it is secret, use an env var or secret store and document the local name
   in `.env.example`.
2. If it is safe to commit but differs by environment, add it to the relevant
   pydantic model in `src/app/config.py` and set or default it in `config.toml`.
3. If it controls process shape, add it to `src/app/runtime.py` and the
   Dockerfile/runtime docs as needed.
4. Update this guide when the setting introduces a new rule or surface.
