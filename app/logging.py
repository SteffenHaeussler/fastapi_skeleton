import logging
import sys

from loguru import logger


def setup_logger(log_level: bool, on_file: bool = False) -> None:

    log_level = logging.DEBUG if log_level else logging.INFO

    logger.add(
        sys.stderr, format="{time} {level} {message}", filter="fastapi", level=log_level
    )

    if on_file:
        logger.add("file.log", rotation="05:00")
