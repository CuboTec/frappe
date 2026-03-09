"""
Provides logging configuration and utilities for the application.

This module configures logging for the application, including integration
with StructLog and optional support for Logstash. It provides functionalities
for setting up logging processors, formatters, and configuring log output for
various environments (e.g., development and production). Additionally, it
provides a utility function for retrieving structured loggers.

Attributes:
    ENVIRONMENT (str): The current environment (e.g., development, production).
    VERSION (str): The version of the application.
    LOG_LEVEL (str): The default logging level.
    LOGSTASH_HOST (str): The host address of the Logstash server.
    LOGSTASH_PORT (int): The port number of the Logstash server.

Functions:
    configure_logging: Configures application-wide logging with StructLog.
    get_logger: Retrieves a StructLog-bound logger with the specified name.
"""
from __future__ import annotations

import logging
import sys
from os import getenv
from typing import List

import logstash
import structlog
from frappe.logging.processors import add_base_contexts

try:
	import frappe
except Exception:
	frappe = None

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


def configure_logging(*, app_name: str) -> None:
	logging.basicConfig(
		format="%(message)s",
		stream=sys.stdout,
		level=_resolve_log_level(LOG_LEVEL),
		force=True
	)

	common_processors: List[structlog.typing.Processor] = [
		structlog.contextvars.merge_contextvars,
		add_base_contexts(ENVIRONMENT, VERSION, app_name),
		structlog.processors.add_log_level,
		structlog.processors.TimeStamper(fmt="iso", utc=True),
		structlog.processors.StackInfoRenderer(),
		structlog.processors.format_exc_info,
		structlog.stdlib.add_logger_name,
		structlog.stdlib.add_log_level,
		structlog.stdlib.PositionalArgumentsFormatter(),
	]

	structlog_processors = [
		*common_processors,
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
			foreign_pre_chain=common_processors
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
				foreign_pre_chain=common_processors
			)
		)
	)

	root_logger = logging.getLogger()
	root_logger.handlers = [main_handler, logstash_handler]
	root_logger.setLevel(logging.INFO)

	structlog.configure(
		processors=structlog_processors,
		logger_factory=structlog.stdlib.LoggerFactory(),
		wrapper_class=structlog.make_filtering_bound_logger(
			_resolve_log_level(LOG_LEVEL)
		),
		cache_logger_on_first_use=True,
	)
