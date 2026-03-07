"""
Provides functionality to configure structured logging and retrieve structured loggers.

This module includes functions to configure logging with adjustable log level, contextual
logging processors, and output formats for different environments. It also provides
support to integrate with external log collectors like Logstash, enabling flexible and
extensible logging in Python applications.

Constants:
    ENVIRONMENT (str): The current application environment, defaults to "development".
    VERSION (str): The application's version information, defaults to "cubo-v15.0.0".
    LOG_LEVEL (str): The level of logging verbosity, defaults to "INFO".

Functions:
    configure_logging: Configures structured logging with processors and handlers.
    get_logger: Retrieves a structured logger instance for use in the application.
"""
from __future__ import annotations

import logging
import sys
from os import getenv
from typing import Any, MutableMapping, Optional, List

import logstash
import structlog

ENVIRONMENT = getenv("ENVIRONMENT", "development")
VERSION = getenv("VERSION", "cubo-v15.0.0")
LOG_LEVEL = getenv("LOG_LEVEL", "INFO")
LOGSTASH_HOST = getenv("LOGSTASH_HOST", "logs.oneglobal.digital")
LOGSTASH_PORT = int(getenv("LOGSTASH_PORT", "5959"))

_LOG_LEVEL_MAP = {
	"DEBUG": logging.DEBUG,
	"INFO": logging.INFO,
	"WARNING": logging.WARNING,
	"ERROR": logging.ERROR,
	"CRITICAL": logging.CRITICAL
}


def _resolve_log_level(log_level: str) -> int:
	return _LOG_LEVEL_MAP.get(log_level.upper(), logging.INFO)


def _add_base_fields(workflow: Optional[str] = None):
	def processor(_: Any, __: str, event_dict: MutableMapping[str, Any]) -> MutableMapping[
		str, Any]:
		event_dict["application"] = f"oneglobal-digital-{ENVIRONMENT}"
		event_dict["workflow"] = workflow or 'frappe'
		event_dict['version'] = VERSION
		return event_dict

	return processor


def configure_logging(*, app_name: str) -> None:
	logging.basicConfig(
		format="%(message)s",
		stream=sys.stdout,
		level=_resolve_log_level(LOG_LEVEL),
		force=True
	)

	processors: List[structlog.typing.Processor] = [
		structlog.contextvars.merge_contextvars,
		_add_base_fields(app_name),
		structlog.processors.add_log_level,
		structlog.processors.TimeStamper(fmt="iso", utc=True),
		structlog.processors.StackInfoRenderer(),
		structlog.processors.format_exc_info,
		structlog.stdlib.add_logger_name,
		structlog.stdlib.add_log_level,
		structlog.stdlib.PositionalArgumentsFormatter(),
		structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
	]

	renderer = structlog.processors.JSONRenderer()
	if ENVIRONMENT == 'development':
		renderer = structlog.dev.ConsoleRenderer()

	main_handler = logging.StreamHandler(sys.stdout)
	main_handler.setLevel(_resolve_log_level(LOG_LEVEL))
	main_handler.setFormatter(
		structlog.stdlib.ProcessorFormatter(
			processor=renderer,
			foreign_pre_chain=processors
		)
	)

	class _BytesFormatter(logging.Formatter):
		def __init__(self, inner: logging.Formatter, encoding: str = "utf-8"):
			super().__init__()
			self._inner = inner
			self._encoding = encoding

		def format(self, record: logging.LogRecord) -> bytes:
			msg = self._inner.format(record)
			if isinstance(msg, bytes):
				return msg
			return str(msg).encode(self._encoding)

	logstash_handler = logstash.TCPLogstashHandler(LOGSTASH_HOST, LOGSTASH_PORT, version=1)
	logstash_handler.setLevel(logging.INFO)
	logstash_handler.setFormatter(
		_BytesFormatter(
			structlog.stdlib.ProcessorFormatter(
				processor=structlog.processors.JSONRenderer(sort_keys=True),
				foreign_pre_chain=processors
			)
		)
	)

	root_logger = logging.getLogger()
	root_logger.handlers = [main_handler, logstash_handler]
	root_logger.setLevel(logging.INFO)

	structlog.configure(
		processors=processors,
		logger_factory=structlog.stdlib.LoggerFactory(),
		wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
		cache_logger_on_first_use=True,
	)


def get_logger(name: str) -> structlog.BoundLogger:
	return structlog.get_logger(name)
