from contextvars import ContextVar


ctx_request_id = ContextVar("request_id", default="-")
ctx_internal_id = ContextVar("internal_id", default="-")
