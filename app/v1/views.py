from time import time

from fastapi import APIRouter, Request
from loguru import logger

from app.v1.errors import *


v1 = APIRouter()


@v1.get("/health")
def health(request: Request):
    logger.debug(f"Methode: {request.method} on {request.url.path}")
    return {"version": request.app.state.VERSION, "timestamp": time()}


@v1.post("/health")
def health(request: Request):
    logger.debug(f"Methode: {request.method} on {request.url.path}")
    return {"version": request.app.state.VERSION, "timestamp": time()}
