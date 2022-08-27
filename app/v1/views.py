from time import time
import logging

from fastapi import APIRouter, Request

from app.v1.errors import *


logger = logging.getLogger()
v1 = APIRouter()


@v1.get("/health")
def health(request: Request):
    logger.debug(f"Methode: {request.method} on {request.url.path}")
    return {"version": request.app.state.VERSION, "timestamp": time()}


@v1.post("/health")
def health(request: Request):
    logger.debug(f"Methode: {request.method} on {request.url.path}")
    return {"version": request.app.state.VERSION, "timestamp": time()}
