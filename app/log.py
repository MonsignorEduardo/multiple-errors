import logging
import os
import sys
from types import TracebackType
from typing import Any

import colorama
import structlog
from structlog.processors import CallsiteParameter
from structlog.types import EventDict, Processor

LOG_LEVEL = "INFO"
LOG_JSON_FORMAT = False


def _set_process_id(_: Any, __: str, event_dict: EventDict) -> EventDict:
    event_dict["process_id"] = os.getpid()
    return event_dict


def _drop_color_message_key(_: Any, __: str, event_dict: EventDict) -> EventDict:
    event_dict.pop("color_message", None)
    return event_dict


def setup_logging() -> None:
    """Set up structured logging configuration for the application.

    This function configures both structlog and standard
    library logging to work together, providing consistent
    log formatting across the application.
    It sets up:

    - Shared processors for both structlog and standard library logging
    - JSON or Console rendering based on LOG_JSON_FORMAT setting
    - Custom color schemes for different log levels in console output
    - Root logger configuration
    - Special handling for third-party loggers (uvicorn, pymongo)
    - Global exception handler to log uncaught exceptions

    The function applies several log processors including:
    - Context variables merging
    - Logger name addition
    - Process ID tracking
    - Log level addition
    - Timestamp in ISO format
    - Stack information
    - Unicode decoding
    - Callsite parameters (filename, function name, line number)

    Global settings used:
    - LOG_JSON_FORMAT: bool - Determines if logs should be in JSON format
    - LOG_LEVEL: str - Sets the root logger's level

    Note:
        This function should be called once at application startup before any
        logging occurs.
        It has side effects as it modifies global logging state.

    Returns:
        None
    """
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        _set_process_id,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.stdlib.ExtraAdder(),
        _drop_color_message_key,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        structlog.processors.CallsiteParameterAdder(
            [
                CallsiteParameter.FILENAME,
                CallsiteParameter.FUNC_NAME,
                CallsiteParameter.LINENO,
            ],
        ),
    ]

    if LOG_JSON_FORMAT:
        # Format the exception only for JSON logs, as we want to pretty-print them when
        # using the ConsoleRenderer
        shared_processors.append(structlog.processors.format_exc_info)

    # == StructLog Config ==
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # == Define the renderer (JSONRenderer or ConsoleRenderer) ==
    log_renderer: structlog.processors.JSONRenderer | structlog.dev.ConsoleRenderer

    if LOG_JSON_FORMAT:
        log_renderer = structlog.processors.JSONRenderer()
    else:
        # Specify a custom color for each log level.
        log_renderer = structlog.dev.ConsoleRenderer(
            colors=True,
            level_styles={
                "debug": colorama.Fore.CYAN,
                "info": colorama.Fore.GREEN,
                "warning": colorama.Fore.YELLOW,
                "error": colorama.Fore.RED,
                "critical": colorama.Fore.RED + colorama.Style.BRIGHT,
            },
        )

    # == Set up the ProcessorFormatter for all logs ==
    formatter = structlog.stdlib.ProcessorFormatter(
        # These run ONLY on `logging` entries that do NOT originate within structlog.
        foreign_pre_chain=shared_processors,
        # These run on ALL entries after the pre_chain is done.
        processors=[
            # Remove _record & _from_structlog.
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            log_renderer,
        ],
    )

    # == Configure the root logger handler ==
    handler = logging.StreamHandler()
    # Use OUR `ProcessorFormatter` to format all `logging` entries.
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(LOG_LEVEL.upper())

    # == Adjust loggers for uvicorn, pymongo, taskiq, etc. ==
    # Remove any handlers from uvicorn loggers and allow logs to propagate
    #   to the root logger.
    for _log in ["uvicorn", "uvicorn.error"]:
        logging.getLogger(_log).handlers.clear()
        logging.getLogger(_log).propagate = True

    # Since we re-create the access logs ourselves, to add all information
    # in the structured log (see the `logging_middleware` in app.py), we clear
    # the handlers and prevent the logs to propagate to a logger higher up in the
    # hierarchy (effectively rendering them silent).
    logging.getLogger("uvicorn.access").handlers.clear()
    logging.getLogger("uvicorn.access").propagate = False

    # Remove pymongo.topology from the logs
    logging.getLogger("pymongo.topology").handlers.clear()
    logging.getLogger("pymongo.topology").propagate = False

    # == Configure taskiq loggers to use structured logging ==
    # Remove any handlers from taskiq loggers and allow logs to propagate
    #   to the root logger, which will use our structured logging setup.
    for _log in ["taskiq", "taskiq.worker", "taskiq.broker", "taskiq.scheduler"]:
        _logger = logging.getLogger(__name__)
        _logger.propagate = False

    def _handle_exception(
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_traceback: TracebackType | None,
    ) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        root_logger.critical(
            "Uncaught exception",
            exc_info=(exc_type, exc_value, exc_traceback),
        )

    # Redirect all uncaught exceptions to the logger
    sys.excepthook = _handle_exception
