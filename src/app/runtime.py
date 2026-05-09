import os
import sys
from dataclasses import dataclass
from typing import Mapping

import uvicorn


@dataclass(frozen=True)
class RuntimeConfig:
    port: int
    workers: int


class RuntimeConfigError(ValueError):
    pass


def _positive_int(env: Mapping[str, str], name: str, default: int) -> int:
    raw_value = env.get(name, str(default))
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise RuntimeConfigError(
            f"{name} must be a positive integer, got {raw_value!r}"
        ) from exc

    if value < 1:
        raise RuntimeConfigError(
            f"{name} must be a positive integer, got {raw_value!r}"
        )

    return value


def get_runtime_config(env: Mapping[str, str] | None = None) -> RuntimeConfig:
    runtime_env = os.environ if env is None else env
    return RuntimeConfig(
        port=_positive_int(runtime_env, "PORT", 5000),
        workers=_positive_int(runtime_env, "WEB_CONCURRENCY", 2),
    )


def main() -> None:
    try:
        config = get_runtime_config()
    except RuntimeConfigError as exc:
        print(f"Runtime configuration error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

    uvicorn.run(
        "src.app.main:app",
        host="0.0.0.0",
        port=config.port,
        workers=config.workers,
        log_level="error",
    )


if __name__ == "__main__":
    main()
