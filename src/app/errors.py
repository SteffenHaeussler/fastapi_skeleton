from pydantic import BaseModel


class ErrorResponse(BaseModel):
    error: str
    message: str
    status: int
    request_id: str
    details: dict | None = None


class APIException(Exception):
    status_code: int = 500
    error_code: str = "internal_server_error"

    def __init__(self, message: str, *, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details
