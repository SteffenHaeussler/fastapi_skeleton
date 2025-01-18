# !/usr/bin/env python
from pathlib import Path
from typing import Dict

from fastapi import FastAPI
from loguru import logger

from src.app.core import views as core_views
from src.app.logging import setup_logger
from src.app.meta import tags_metadata
from src.app.middleware import RequestTimer, add_request_id
from src.app.settings import Settings
from src.app.v1 import views as v1_view

BASEDIR = Path(__file__).resolve().parent
ROOTDIR = BASEDIR.parents[1]


def get_application(settings: Dict) -> FastAPI:
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
    application = FastAPI(openapi_tags=tags_metadata)

    application.state = settings

    application.middleware("http")(request_timer)
    application.middleware("http")(add_request_id)

    application.include_router(core_views.core, tags=["core"])

    application.include_router(v1_view.v1, prefix="/v1", tags=["v1"])

    logger.info(f"API running in {settings.api_mode.CONFIG_NAME} mode")
    return application


# ugly work around to set the toml file path
Settings._toml_file = f"{ROOTDIR}/config.toml"
settings = Settings()

setup_logger(settings.api_mode)
app = get_application(settings)
