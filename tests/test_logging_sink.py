import io
import json
import sys
from contextlib import redirect_stdout

from loguru import logger

from src.app.logging import setup_logger


def test_sink_serializer_includes_extra_fields():
    setup_logger("DEV", json_serialize=True)
    buf = io.StringIO()
    with redirect_stdout(buf):
        logger.bind(method="GET", path="/x", status=200, duration_ms=1.2).info(
            "request"
        )
        sys.stdout.flush()
    line = buf.getvalue().strip().splitlines()[-1]
    payload = json.loads(line)
    assert payload["message"] == "request"
    assert payload["method"] == "GET"
    assert payload["path"] == "/x"
    assert payload["status"] == 200
    assert payload["duration_ms"] == 1.2
    assert "request_id" in payload
