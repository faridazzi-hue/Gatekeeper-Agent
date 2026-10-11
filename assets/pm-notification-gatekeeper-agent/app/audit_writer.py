"""Audit writer for the Plant Maintenance Notification Gatekeeper Agent.

Writes a structured audit record to the configured destination after every
notification review. Records are written as JSON lines (one record per line)
to support easy ingestion and querying.

The audit writer never raises exceptions that would interrupt the agent flow —
all errors are logged and surfaced in the audit record itself.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config_loader import get_audit_storage

logger = logging.getLogger(__name__)


def write_audit_record(record: dict[str, Any]) -> str:
    """Write a structured audit record to the configured destination.

    Args:
        record: Dict containing all required audit fields. Missing fields are
                filled with None rather than raising an exception.

    Returns:
        String summary: 'written:<destination>' or 'error:<message>'.
    """
    # Ensure required fields are present with defaults
    audit_entry = {
        "notification_number": record.get("notification_number"),
        "plant": record.get("plant"),
        "review_timestamp": record.get(
            "review_timestamp", datetime.now(timezone.utc).isoformat()
        ),
        "checks_performed": record.get("checks_performed", []),
        "validation_results": record.get("validation_results", []),
        "duplicate_candidates": record.get("duplicate_candidates", []),
        "agent_recommendation": record.get("agent_recommendation"),
        "confidence_level": record.get("confidence_level"),
        "gatekeeper_selection": record.get("gatekeeper_selection"),
        "override_justification": record.get("override_justification"),
        "sap_action_requested": record.get("sap_action_requested"),
        "api_response": record.get("api_response"),
        "resulting_sap_status": record.get("resulting_sap_status"),
        "email_draft_reference": record.get("email_draft_reference"),
        "errors": record.get("errors", []),
        "is_partial": record.get("is_partial", False),
    }

    try:
        storage_cfg = get_audit_storage()
        storage_type = storage_cfg.get("type", "stdout")

        if storage_type == "file":
            path = Path(storage_cfg["path"])
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(audit_entry, ensure_ascii=False) + "\n")
            logger.info(
                "Audit record written for notification %s to %s",
                audit_entry["notification_number"],
                path,
            )
            return f"written:{path}"

        elif storage_type == "stdout":
            print(json.dumps(audit_entry, ensure_ascii=False), file=sys.stdout)
            return "written:stdout"

        else:
            msg = f"Unknown audit storage type: {storage_type}"
            logger.error(msg)
            return f"error:{msg}"

    except Exception as exc:  # pylint: disable=broad-except
        msg = f"Failed to write audit record for notification {audit_entry.get('notification_number')}: {exc}"
        logger.error(msg, exc_info=True)
        return f"error:{msg}"


def build_partial_audit_record(
    notification_number: str | None,
    plant: str | None,
    error: str,
) -> dict[str, Any]:
    """Build a minimal audit record for a failed or incomplete review.

    Args:
        notification_number: Notification being reviewed (may be None if retrieval failed).
        plant: Plant identifier for the session.
        error: Description of the failure or incomplete state.

    Returns:
        Partial audit record dict ready to pass to write_audit_record().
    """
    return {
        "notification_number": notification_number,
        "plant": plant,
        "review_timestamp": datetime.now(timezone.utc).isoformat(),
        "is_partial": True,
        "errors": [error],
    }
