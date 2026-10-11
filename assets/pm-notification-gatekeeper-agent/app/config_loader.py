"""Configuration loader for the Plant Maintenance Notification Gatekeeper Agent.

Loads agent_config.yaml from app/config/ at startup. The configuration is
read once and cached. Call reload_config() to pick up changes without restarting.
"""

import logging
import os
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).parent / "config" / "agent_config.yaml"
_config: dict[str, Any] | None = None

# Required top-level keys that must be present in the configuration file.
REQUIRED_KEYS = [
    "sap_destination",
    "action_to_status_mapping",
    "notification_types_in_scope",
    "screening_status",
    "open_statuses_for_duplicate_detection",
    "worklist_prioritization",
    "audit_storage",
]


def _load() -> dict[str, Any]:
    """Load and validate the configuration file."""
    config_path = Path(os.environ.get("AGENT_CONFIG_PATH", str(_CONFIG_PATH)))
    if not config_path.exists():
        raise FileNotFoundError(
            f"Agent configuration file not found: {config_path}. "
            "Ensure app/config/agent_config.yaml exists before starting the agent."
        )
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if not isinstance(cfg, dict):
        raise ValueError(f"Configuration file must be a YAML mapping: {config_path}")
    missing = [k for k in REQUIRED_KEYS if k not in cfg]
    if missing:
        raise ValueError(
            f"Agent configuration is missing required keys: {missing}. "
            f"Check {config_path} and add the missing entries."
        )
    logger.info("Agent configuration loaded from %s", config_path)
    return cfg


def get_config() -> dict[str, Any]:
    """Return the cached configuration, loading it on first call."""
    global _config
    if _config is None:
        _config = _load()
    return _config


def reload_config() -> dict[str, Any]:
    """Force a reload of the configuration file."""
    global _config
    _config = _load()
    return _config


def get_sap_destination() -> str:
    return get_config()["sap_destination"]


def get_action_mapping(decision: str) -> dict[str, str]:
    """Return the API action and expected status for a gatekeeper decision.

    Args:
        decision: One of 'approve', 'reject', 'rework', 'in_process', 'complete'.

    Returns:
        Dict with 'api_action' and 'expected_status'.

    Raises:
        KeyError: If the decision is not in the mapping.
    """
    mapping = get_config()["action_to_status_mapping"]
    if decision not in mapping:
        raise KeyError(
            f"Decision '{decision}' not found in action_to_status_mapping. "
            f"Valid decisions: {list(mapping.keys())}"
        )
    return mapping[decision]


def get_notification_types_in_scope() -> list[str]:
    return get_config()["notification_types_in_scope"]


def get_screening_status() -> str:
    return get_config()["screening_status"]


def get_open_statuses_for_duplicate_detection() -> list[str]:
    return get_config()["open_statuses_for_duplicate_detection"]


def get_valid_code_groups() -> list[dict]:
    return get_config().get("valid_code_groups", [])


def get_failure_groups() -> list[dict]:
    return get_config().get("failure_groups", [])


def get_attachment_requirements() -> list[dict]:
    return get_config().get("attachment_requirements", [])


def get_worklist_weights() -> dict[str, int]:
    return get_config()["worklist_prioritization"]


def get_audit_storage() -> dict[str, str]:
    return get_config()["audit_storage"]


def get_email_draft_settings() -> dict:
    return get_config().get("email_draft", {"outlook_integration": False, "language": "en"})
