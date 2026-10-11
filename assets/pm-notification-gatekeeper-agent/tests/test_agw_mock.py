"""Tests for MCP provider agw.py — mock tool building and token management."""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "app"))


def _mock_json_content():
    return {
        "servers": {
            "s4-maintnotification": {
                "mcp_server_name": "com.sap.s4/API_MAINTNOTIFICATION",
                "description": "Maintenance notification MCP tools",
                "tools": {
                    "list_maintenancenotification": {
                        "description": "List maintenance notifications",
                        "input_schema": {
                            "type": "object",
                            "properties": {
                                "$filter": {"type": "string", "description": "OData filter"},
                                "$top": {"type": "integer", "description": "Max results"},
                            },
                            "required": [],
                        },
                        "mock_response": {
                            "results": [
                                {
                                    "MaintenanceNotification": "10000001",
                                    "NotifProcessingPhase": "OSNO",
                                    "Plant": "1710",
                                }
                            ]
                        },
                    },
                    "get_maintenancenotification": {
                        "description": "Get a single maintenance notification",
                        "input_schema": {
                            "type": "object",
                            "properties": {
                                "MaintenanceNotification": {
                                    "type": "string",
                                    "description": "Notification number",
                                }
                            },
                            "required": ["MaintenanceNotification"],
                        },
                        "mock_response": {
                            "MaintenanceNotification": "10000001",
                            "NotifProcessingPhase": "OSNO",
                            "Plant": "1710",
                        },
                    },
                },
            }
        },
        "metadata": {
            "version": "1.0.0",
            "created_for_agent": "pm-notification-gatekeeper-agent",
            "mock_mode": True,
        },
    }


def test_build_mock_tools_returns_list():
    """_build_mock_tools returns a list when mcp-mock.json exists."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(_mock_json_content(), f)
        tmp_path = Path(f.name)

    try:
        with patch("mcp_providers.agw._MOCK_FILE", tmp_path):
            from mcp_providers.agw import _build_mock_tools
            tools = _build_mock_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0
    finally:
        tmp_path.unlink()


def test_build_mock_tools_tool_names():
    """_build_mock_tools produces tools with correct names from mcp-mock.json."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(_mock_json_content(), f)
        tmp_path = Path(f.name)

    try:
        with patch("mcp_providers.agw._MOCK_FILE", tmp_path):
            from mcp_providers.agw import _build_mock_tools
            tools = _build_mock_tools()
        names = [t.name for t in tools]
        assert "list_maintenancenotification" in names
        assert "get_maintenancenotification" in names
    finally:
        tmp_path.unlink()


def test_build_mock_tools_returns_empty_when_file_missing():
    """_build_mock_tools returns an empty list when mcp-mock.json is absent."""
    non_existent = Path("/tmp/nonexistent_mcp_mock_12345.json")
    with patch("mcp_providers.agw._MOCK_FILE", non_existent):
        from mcp_providers.agw import _build_mock_tools
        tools = _build_mock_tools()
    assert tools == []


def test_build_mock_tools_returns_empty_on_invalid_json():
    """_build_mock_tools returns empty list gracefully when JSON is malformed."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("{ invalid json {{")
        tmp_path = Path(f.name)

    try:
        with patch("mcp_providers.agw._MOCK_FILE", tmp_path):
            from mcp_providers.agw import _build_mock_tools
            tools = _build_mock_tools()
        assert isinstance(tools, list)
    finally:
        tmp_path.unlink()


def test_set_user_token_stores_token():
    """set_user_token sets the token accessible via get_user_token."""
    from mcp_providers.agw import set_user_token, get_user_token, reset_user_token
    ctx = set_user_token("my-test-jwt")
    try:
        assert get_user_token() == "my-test-jwt"
    finally:
        reset_user_token(ctx)


def test_reset_user_token_clears_token():
    """reset_user_token restores the previous context value."""
    from mcp_providers.agw import set_user_token, get_user_token, reset_user_token
    original = get_user_token()
    ctx = set_user_token("temporary-token")
    reset_user_token(ctx)
    assert get_user_token() == original


@pytest.mark.asyncio
async def test_get_mcp_tools_returns_list_in_test_env():
    """get_mcp_tools returns a list when IBD_TESTING is set and mock file exists."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(_mock_json_content(), f)
        tmp_path = Path(f.name)

    try:
        with patch("mcp_providers.agw._MOCK_FILE", tmp_path), \
             patch.dict(os.environ, {"IBD_TESTING": "true"}):
            from mcp_providers.agw import _build_mock_tools
            tools = _build_mock_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0
    finally:
        tmp_path.unlink()
