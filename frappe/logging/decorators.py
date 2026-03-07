"""
This module provides functionality for logging contextual information during the execution
of decorated functions. It includes a decorator to bind event-specific context for log entries
and record execution details such as start, success, and error occurrences.
"""
from __future__ import annotations

from functools import wraps

from frappe.logging.context import bound_event_context
from frappe.logging.logger import get_logger


def log_context(*, event: str, name: str):

	def log_context_decorator(func):
		logger = get_logger(name)

		@wraps(func)
		def wrapper(*args, **kwargs):
			with bound_event_context(event):
				logger.info(f"Starting execution of {func.__name__}")
				try:
					result = func(*args, **kwargs)
					logger.info(f"Executed {func.__name__} successfully")
					return result
				except Exception as e:
					logger.error(f"Error occurred while executing {func.__name__} with event '{event}': {str(e)}")
					raise e

		return wrapper

	return log_context_decorator
