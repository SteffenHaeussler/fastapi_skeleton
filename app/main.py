# !/usr/bin/env python
import os

from fastapi import FastAPI, Request, Response
from loguru import logger

from app.config import config
from app.logging import setup_logger
from app.meta import tags_metadata
from app.core import views as core_views
from app.v1 import views as v1_view
from app.middleware import RequestTimer


def get_application(config_name: str) -> FastAPI:
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

    application.state = config[config_name]
    setup_logger(application.state.DEBUG, application.state.ON_PREMISE)

    application.middleware("http")(request_timer)

    application.include_router(core_views.core, tags=["core"])

    application.include_router(v1_view.v1, prefix="/v1", tags=["v1"])

    logger.info(f"API running in {config_name.upper()} mode")

    return application


api_mode = os.getenv("FASTAPI_ENV") or "develop"
app = get_application(api_mode)


