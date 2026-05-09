# !/usr/bin/env python
from pathlib import Path
from typing import Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from src.app.config import Config
from src.app.core import router as core_router
from src.app.errors import register_exception_handlers
from src.app.lifespan import lifespan
from src.app.logging import setup_logger
from src.app.meta import tags_metadata
from src.app.middleware import RequestTimer, add_request_id
from src.app.v1 import router as v1_router

BASEDIR = Path(__file__).resolve().parent
ROOTDIR = BASEDIR.parents[1]


def get_application(config: Dict) -> FastAPI:
    """
    Create the FastAPI app.

    Params

    config_name: string
        sets specific config flags

    Returns:

    app: object
        fastapi app
    -------
    """
    request_timer = RequestTimer()
    application = FastAPI(lifespan=lifespan, openapi_tags=tags_metadata)

    for key in config.model_fields:
        setattr(application.state, key, getattr(config, key))

    cors = config.api_mode.cors
    if cors.enabled:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=cors.allow_origins,
            allow_methods=cors.allow_methods,
            allow_headers=cors.allow_headers,
            allow_credentials=cors.allow_credentials,
        )

    application.middleware("http")(request_timer)
    application.middleware("http")(add_request_id)
    register_exception_handlers(application)

    application.include_router(core_router.core, tags=["core"])

    application.include_router(v1_router.v1, prefix="/v1", tags=["v1"])

    logger.info(f"API running in {config.api_mode.CONFIG_NAME} mode")
    return application


# ugly work around to set the toml file path
Config._toml_file = f"{ROOTDIR}/config.toml"
config = Config()

setup_logger(config.api_mode.CONFIG_NAME)
app = get_application(config)
