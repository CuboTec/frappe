"""
This module provides utilities for binding and unbinding contextual logging variables
to structlog's contextvars, specifically for trace IDs and event contexts.

The module includes functions to set a unique trace ID in the logging context, bind an
event-specific context, and unbind the event context. Additionally, it provides a context
manager to temporarily bind an event context during the scope of operations.

Functions:
    - set_trace_id_context: Set a unique trace ID in the logging context.
    - bind_event_context: Bind an event context to structlog's contextvars.
    - unbind_event_context: Unbind the event context.
    - bound_event_context: Context manager to provide scoped binding for event contexts.
"""
from __future__ import annotations

import uuid
from contextlib import contextmanager
from typing import Iterator

from structlog.contextvars import bind_contextvars, unbind_contextvars


def set_trace_id_context():
	bind_contextvars(trace_id=str(uuid.uuid4()))


def bind_event_context(event):
	bind_contextvars(event=event)


def unbind_event_context():
	unbind_contextvars('event')


@contextmanager
def bound_event_context(name: str) -> Iterator[None]:
	bind_event_context(name)
	try:
		yield
	finally:
		unbind_event_context()


