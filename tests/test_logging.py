from __future__ import annotations

import io

from ism.logging import configure_logging


def test_p0_io_002_logging_initialization_is_idempotent() -> None:
    stream = io.StringIO()
    first = configure_logging(stream=stream)
    second = configure_logging(stream=stream)

    assert first is second
    assert len(first.handlers) == 1

    first.info("once")
    assert stream.getvalue().count("once") == 1
