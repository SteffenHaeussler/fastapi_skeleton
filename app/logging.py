import logging
import json

from fastapi import Request
from uvicorn.logging import DefaultFormatter

from app.context import ctx_request_id


class RequestIdFilter(logging.Filter):
    """Logging filter to add request IDs to log records"""

    def __init__(self, param=None):
        self.param = param

    def filter(self, record) -> bool:
        r_id = ctx_request_id.get()
        record.request_id = r_id
        return True


class JsonFormatter(DefaultFormatter):
    """
    https://stackoverflow.com/a/70223539


    Formatter that outputs JSON strings after parsing the LogRecord.

    Args:
        - fmt_dict: Key: logging format attribute pairs. Defaults to {"message": "message"}.
        - time_format: time.strftime() format string. Default: "%Y-%m-%dT%H:%M:%S"
        - msec_format: Microsecond formatting. Appended at the end. Default: "%s.%03dZ"
    """

    def __init__(
        self,
        fmt: dict = None,
        time_format: str = "%Y-%m-%dT%H:%M:%S",
        msec_format: str = "%s.%03dZ",
    ):

        self.fmt_dict = fmt if fmt is not None else {"message": "message"}
        self.default_time_format = time_format
        self.default_msec_format = msec_format
        self.datefmt = None

    def usesTime(self) -> bool:
        """
        Overwritten to look for the attribute in the format dict values instead of the fmt string.
        """
        return "asctime" in self.fmt_dict.values()

    def formatMessage(self, record) -> dict:
        """
        Overwritten to return a dictionary of the relevant LogRecord attributes instead of a string.
        KeyError is raised if an unknown attribute is provided in the fmt_dict.
        """
        return {
            fmt_key: record.__dict__[fmt_val]
            for fmt_key, fmt_val in self.fmt_dict.items()
        }

    def format(self, record) -> str:
        """
        Mostly the same as the parent's class method, the difference being that a dict is manipulated and dumped as JSON
        instead of a string.
        """
        record.message = record.getMessage()

        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)

        message_dict = self.formatMessage(record)

        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)

        if record.exc_text:
            message_dict["exc_info"] = record.exc_text

        if record.stack_info:
            message_dict["stack_info"] = self.formatStack(record.stack_info)

        return json.dumps(message_dict, default=str)


