"""Tests for config_loader module."""

import os
import pytest
import yaml
import tempfile
from pathlib import Path


def test_get_config_loads_successfully():
    """Config loads from the default path without error."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "app"))
    from config_loader import get_config, reload_config
    reload_config()
    cfg = get_config()
    assert isinstance(cfg, dict)
    assert cfg["sap_destination"] == "S4HANA_QUALITY"


def test_get_config_required_keys():
    """All required keys are present in the default config."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "app"))
    from config_loader import get_config, REQUIRED_KEYS, reload_config
    reload_config()
    cfg = get_config()
    for key in REQUIRED_KEYS:
        assert key in cfg, f"Required key '{key}' missing from config"


def test_get_sap_destination():
    """SAP destination returns S4HANA_QUALITY."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "app"))
    from config_loader import get_sap_destination, reload_config
    reload_config()
    assert get_sap_destination() == "S4HANA_QUALITY"


def test_get_action_mapping_approve():
    """Approve action maps to ApproveMaintWorkRequest."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "app"))
    from config_loader import get_action_mapping, reload_config
    reload_config()
    mapping = get_action_mapping("approve")
    assert mapping["api_action"] == "ApproveMaintWorkRequest"
    assert "expected_status" in mapping


def test_get_action_mapping_reject():
    """Reject action maps to RejectMaintWorkRequest."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "app"))
    from config_loader import get_action_mapping, reload_config
    reload_config()
    mapping = get_action_mapping("reject")
    assert mapping["api_action"] == "RejectMaintWorkRequest"


def test_get_action_mapping_rework():
    """Rework action maps to SetMaintNotifToInfoRequired."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "app"))
    from config_loader import get_action_mapping, reload_config
    reload_config()
    mapping = get_action_mapping("rework")
    assert mapping["api_action"] == "SetMaintNotifToInfoRequired"
    assert mapping["expected_status"] == "NOPO"


def test_get_action_mapping_invalid_decision():
    """Invalid decision raises KeyError."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "app"))
    from config_loader import get_action_mapping, reload_config
    reload_config()
    with pytest.raises(KeyError):
        get_action_mapping("unknown_decision")


def test_missing_required_key_raises_error():
    """Config file missing a required key raises ValueError on load."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

    minimal = {"sap_destination": "S4HANA_QUALITY"}  # missing all other required keys
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(minimal, f)
        tmp_path = f.name

    try:
        os.environ["AGENT_CONFIG_PATH"] = tmp_path
        from config_loader import reload_config
        with pytest.raises(ValueError, match="missing required keys"):
            reload_config()
    finally:
        del os.environ["AGENT_CONFIG_PATH"]
        os.unlink(tmp_path)
        from config_loader import reload_config
        reload_config()


def test_get_notification_types_in_scope():
    """Returns M1 and M2 as in-scope notification types."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "app"))
    from config_loader import get_notification_types_in_scope, reload_config
    reload_config()
    types = get_notification_types_in_scope()
    assert "M1" in types
    assert "M2" in types


def test_get_screening_status():
    """Returns OSNO as screening status."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "app"))
    from config_loader import get_screening_status, reload_config
    reload_config()
    assert get_screening_status() == "OSNO"


def test_open_statuses_excludes_noco():
    """Open statuses for duplicate detection do not include NOCO."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "app"))
    from config_loader import get_open_statuses_for_duplicate_detection, reload_config
    reload_config()
    statuses = get_open_statuses_for_duplicate_detection()
    assert "OSNO" in statuses
    assert "NOPR" in statuses
    assert "NOCO" not in statuses
