"""Tests for audit_writer module."""

import json
import os
import sys
import tempfile
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "app"))


def _write_temp_config_with_audit_path(tmp_path):
    """Write a minimal config pointing audit to a temp file."""
    import yaml
    cfg = {
        "sap_destination": "S4HANA_QUALITY",
        "action_to_status_mapping": {
            "approve": {"api_action": "ApproveMaintWorkRequest", "expected_status": "NOPR"},
            "reject": {"api_action": "RejectMaintWorkRequest", "expected_status": "REJA"},
            "rework": {"api_action": "SetMaintNotifToInfoRequired", "expected_status": "NOPO"},
            "in_process": {"api_action": "SetMaintNotifToInProcess", "expected_status": "NOPR"},
            "complete": {"api_action": "CompleteMaintNotification", "expected_status": "NOCO"},
        },
        "notification_types_in_scope": ["M1", "M2"],
        "screening_status": "OSNO",
        "open_statuses_for_duplicate_detection": ["OSNO", "NOPR"],
        "worklist_prioritization": {"abc_a_equipment": 30},
        "audit_storage": {"type": "file", "path": str(tmp_path)},
        "email_draft": {"outlook_integration": False, "language": "en"},
    }
    config_file = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    yaml.dump(cfg, config_file)
    config_file.close()
    return config_file.name


def test_write_audit_record_to_file():
    """Audit record is written as a JSON line to the configured file."""
    audit_file = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
    audit_file.close()
    config_file = _write_temp_config_with_audit_path(audit_file.name)

    try:
        os.environ["AGENT_CONFIG_PATH"] = config_file
        from config_loader import reload_config
        reload_config()
        from audit_writer import write_audit_record
        record = {
            "notification_number": "10000001",
            "plant": "1710",
            "agent_recommendation": "Approve",
            "confidence_level": "High",
            "gatekeeper_selection": "Accept",
        }
        result = write_audit_record(record)
        assert result.startswith("written:")

        with open(audit_file.name) as f:
            lines = f.readlines()
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["notification_number"] == "10000001"
        assert parsed["agent_recommendation"] == "Approve"
    finally:
        del os.environ["AGENT_CONFIG_PATH"]
        os.unlink(audit_file.name)
        os.unlink(config_file)
        from config_loader import reload_config
        reload_config()


def test_write_multiple_audit_records_append():
    """Multiple audit records are appended as separate JSON lines."""
    audit_file = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
    audit_file.close()
    config_file = _write_temp_config_with_audit_path(audit_file.name)

    try:
        os.environ["AGENT_CONFIG_PATH"] = config_file
        from config_loader import reload_config
        reload_config()
        from audit_writer import write_audit_record
        write_audit_record({"notification_number": "10000001", "plant": "1710"})
        write_audit_record({"notification_number": "10000002", "plant": "1710"})

        with open(audit_file.name) as f:
            lines = f.readlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["notification_number"] == "10000001"
        assert json.loads(lines[1])["notification_number"] == "10000002"
    finally:
        del os.environ["AGENT_CONFIG_PATH"]
        os.unlink(audit_file.name)
        os.unlink(config_file)
        from config_loader import reload_config
        reload_config()


def test_partial_audit_record_marks_is_partial():
    """Partial audit record has is_partial=True and records the error."""
    from audit_writer import build_partial_audit_record
    record = build_partial_audit_record("10000001", "1710", "Backend unavailable")
    assert record["is_partial"] is True
    assert "Backend unavailable" in record["errors"]
    assert record["notification_number"] == "10000001"
    assert record["plant"] == "1710"


def test_partial_audit_record_null_notification():
    """Partial record can be built even when notification number is unknown."""
    from audit_writer import build_partial_audit_record
    record = build_partial_audit_record(None, "1710", "Query failed before notification retrieved")
    assert record["notification_number"] is None
    assert record["is_partial"] is True


def test_write_audit_record_does_not_raise_on_bad_config():
    """Audit writer handles storage errors gracefully without raising."""
    audit_file = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
    audit_file.close()
    config_file = _write_temp_config_with_audit_path("/nonexistent/path/that/cannot/be/created/audit.jsonl")

    try:
        os.environ["AGENT_CONFIG_PATH"] = config_file
        from config_loader import reload_config
        reload_config()
        from audit_writer import write_audit_record
        # Should not raise — errors are logged and returned as a string
        result = write_audit_record({"notification_number": "10000001"})
        assert result.startswith("error:")
    finally:
        del os.environ["AGENT_CONFIG_PATH"]
        os.unlink(audit_file.name)
        os.unlink(config_file)
        from config_loader import reload_config
        reload_config()
