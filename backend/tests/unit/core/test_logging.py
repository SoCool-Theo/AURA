import importlib
import logging

import pytest

import backend.app.core.logging as logging_module


def _remove_new_aura_handlers(
    root_logger: logging.Logger,
    original_handlers: tuple[logging.Handler, ...],
) -> None:
    marker = logging_module._AURA_HANDLER_MARKER
    for handler in list(root_logger.handlers):
        if handler not in original_handlers and getattr(handler, marker, False):
            root_logger.removeHandler(handler)
            handler.close()


def test_import_alone_does_not_configure_global_logging() -> None:
    root_logger = logging.getLogger()
    handlers_before = tuple(root_logger.handlers)
    level_before = root_logger.level

    importlib.reload(logging_module)

    assert tuple(root_logger.handlers) == handlers_before
    assert root_logger.level == level_before


def test_configure_logging_adds_one_reusable_info_console_handler() -> None:
    root_logger = logging.getLogger()
    original_handlers = tuple(root_logger.handlers)
    original_level = root_logger.level
    marker = logging_module._AURA_HANDLER_MARKER
    unrelated_handler = logging.NullHandler()
    root_logger.addHandler(unrelated_handler)

    try:
        logging_module.configure_logging()
        logging_module.configure_logging()

        aura_handlers = [
            handler
            for handler in root_logger.handlers
            if getattr(handler, marker, False)
        ]
        assert root_logger.level == logging.INFO
        assert len(aura_handlers) == 1
        assert isinstance(aura_handlers[0], logging.StreamHandler)
        assert aura_handlers[0].level == logging.INFO
        assert unrelated_handler in root_logger.handlers
    finally:
        root_logger.removeHandler(unrelated_handler)
        unrelated_handler.close()
        _remove_new_aura_handlers(root_logger, original_handlers)
        root_logger.setLevel(original_level)


def test_configure_logging_preserves_pytest_log_capture(
    caplog: pytest.LogCaptureFixture,
) -> None:
    root_logger = logging.getLogger()
    original_handlers = tuple(root_logger.handlers)
    original_level = root_logger.level
    test_logger = logging.getLogger(f"{__name__}.capture")

    try:
        with caplog.at_level(logging.INFO, logger=test_logger.name):
            logging_module.configure_logging()
            test_logger.info("capture remains active")

        assert "capture remains active" in caplog.text
    finally:
        _remove_new_aura_handlers(root_logger, original_handlers)
        root_logger.setLevel(original_level)
