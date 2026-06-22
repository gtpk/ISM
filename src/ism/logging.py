from __future__ import annotations

import logging
from typing import TextIO

_HANDLER_MARKER = "_ism_handler"


def configure_logging(
    *,
    level: int = logging.INFO,
    stream: TextIO | None = None,
) -> logging.Logger:
    logger = logging.getLogger("ism")
    logger.setLevel(level)
    logger.propagate = False

    handler = next(
        (item for item in logger.handlers if getattr(item, _HANDLER_MARKER, False)),
        None,
    )
    if handler is None:
        handler = logging.StreamHandler(stream)
        setattr(handler, _HANDLER_MARKER, True)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        logger.addHandler(handler)
    handler.setLevel(level)
    return logger
