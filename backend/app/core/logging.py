"""Explicit standard-library logging configuration for Aura processes."""

import logging


_AURA_HANDLER_MARKER = "_aura_console_handler"
_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def configure_logging() -> None:
    """Configure one reusable INFO-level console handler on the root logger."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    aura_handlers = [
        handler
        for handler in root_logger.handlers
        if getattr(handler, _AURA_HANDLER_MARKER, False)
    ]
    if aura_handlers:
        handler = aura_handlers[0]
        for duplicate in aura_handlers[1:]:
            root_logger.removeHandler(duplicate)
            duplicate.close()
    else:
        handler = logging.StreamHandler()
        setattr(handler, _AURA_HANDLER_MARKER, True)
        root_logger.addHandler(handler)

    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
