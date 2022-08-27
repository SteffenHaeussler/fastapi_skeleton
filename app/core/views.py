from time import time
import logging

from fastapi import APIRouter, Request

from . import errors


core = APIRouter()
logger = logging.getLogger()


@core.get("/health")
def health(request: Request):
    logger.debug(f"Methode: {request.method} on {request.url.path}")
    return {"version": request.app.state.VERSION, "timestamp": time()}


@core.post("/health")
def health(request: Request):
    logger.debug(f"Methode: {request.method} on {request.url.path}")
    return {"version": request.app.state.VERSION, "timestamp": time()}
