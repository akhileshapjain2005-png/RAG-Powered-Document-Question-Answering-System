"""Structured audit logging for compliance and incident response."""

import json
import logging
import os
from typing import Any, Dict, Optional

_audit = logging.getLogger("app.audit")

# Set AUDIT_LOG_ENABLED=false to disable (not recommended for production)
_AUDIT_ENABLED = os.getenv("AUDIT_LOG_ENABLED", "true").lower() == "true"


def audit_event(
    action: str,
    *,
    subject: Optional[str] = None,
    tenant_id: Optional[str] = None,
    auth_method: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    outcome: str = "success",
    request_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """Emit one JSON line per event for log aggregation (Splunk, ELK, CloudWatch)."""
    if not _AUDIT_ENABLED:
        return
    payload: Dict[str, Any] = {
        "event": "audit",
        "action": action,
        "outcome": outcome,
    }
    if subject is not None:
        payload["subject"] = subject
    if tenant_id is not None:
        payload["tenant_id"] = tenant_id
    if auth_method is not None:
        payload["auth_method"] = auth_method
    if resource_type is not None:
        payload["resource_type"] = resource_type
    if resource_id is not None:
        payload["resource_id"] = resource_id
    if request_id is not None:
        payload["request_id"] = request_id
    if extra:
        payload["extra"] = extra
    _audit.info(json.dumps(payload, default=str))

