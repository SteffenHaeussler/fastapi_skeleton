from typing import Literal

from pydantic import BaseModel


class HealthCheckResponse(BaseModel):
    version: str
    timestamp: float


class LivenessResponse(BaseModel):
    status: Literal["ok"]


class ReadinessResponse(BaseModel):
    status: Literal["ok", "degraded"]
    checks: dict[str, Literal["ok", "fail"]]
