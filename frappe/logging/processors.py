"""
A module for adding context data to event dictionaries, tailored for application
logging and enhanced with optional Frappe framework integration.

This module provides utility functions to augment event dictionaries with
contextual data such as environment, version, workflow, and Frappe-specific
data when available. It ensures that relevant contextual information is included
for more meaningful logs.

"""
from __future__ import annotations

import socket
from typing import Any, MutableMapping, Optional

try:
	import frappe
except Exception:
	frappe = None


def _add_frappe_context(event_dict: MutableMapping[str, Any]):
	if frappe:
		try:
			if local := getattr(frappe, "local"):
				event_dict.setdefault("site", getattr(local, "site", None))
				event_dict.setdefault("request_id", getattr(local, "request_id", None))

				if hasattr(local, "form_dict") and local.form_dict:
					cmd = local.form_dict.get("cmd")
					if cmd:
						event_dict.setdefault("cmd", cmd)

				session = getattr(local, "session", None)
				if session:
					user = getattr(session, "user", None)
					if user:
						event_dict.setdefault("user", user)

				request = getattr(local, "request", None)
				if request:
					path = getattr(request, "path", None)
					method = getattr(request, "method", None)

					if path:
						event_dict.setdefault("path", path)
					if method:
						event_dict.setdefault("http_method", method)
		except Exception:
			pass
	event_dict.setdefault("hostname", socket.gethostname())


def add_base_contexts(environment: str, version: str, workflow: Optional[str] = None):
	def processor(_: Any, __: str, event_dict: MutableMapping[str, Any]) -> MutableMapping[
		str, Any]:
		event_dict.setdefault("application", f"oneglobal-digital-{environment}")
		event_dict.setdefault("workflow", workflow or 'frappe')
		event_dict.setdefault("version", version)
		_add_frappe_context(event_dict)
		return event_dict

	return processor
