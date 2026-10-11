"""Tests for load_skill_resources — agent runtime skill loading."""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "app"))


def test_get_load_skill_resource_tool_returns_list():
    """get_load_skill_resource_tool returns a list of tools."""
    from load_skill_resources import get_load_skill_resource_tool
    tools = get_load_skill_resource_tool()
    assert isinstance(tools, list)


def test_skill_tool_has_name():
    """Each tool returned has a non-empty name."""
    from load_skill_resources import get_load_skill_resource_tool
    tools = get_load_skill_resource_tool()
    for tool in tools:
        assert hasattr(tool, "name")
        assert len(tool.name) > 0


def test_skill_tool_has_description():
    """Each skill tool has a non-empty description."""
    from load_skill_resources import get_load_skill_resource_tool
    tools = get_load_skill_resource_tool()
    for tool in tools:
        assert hasattr(tool, "description")


def test_skills_directory_contains_expected_skills():
    """Skills directory contains the four required runtime skills."""
    skills_dir = Path(__file__).parent.parent / "app" / "skills"
    expected = [
        "consistency-validation",
        "duplicate-detection",
        "recommendation",
        "sap-action-mapping",
    ]
    for skill_name in expected:
        skill_path = skills_dir / skill_name / "SKILL.md"
        assert skill_path.exists(), f"Missing skill: {skill_name}/SKILL.md"


def test_consistency_validation_skill_has_valid_frontmatter():
    """Consistency validation SKILL.md has required YAML frontmatter fields."""
    skill_path = Path(__file__).parent.parent / "app" / "skills" / "consistency-validation" / "SKILL.md"
    content = skill_path.read_text()
    assert "name: consistency-validation" in content
    assert "description:" in content


def test_duplicate_detection_skill_has_valid_frontmatter():
    """Duplicate detection SKILL.md has required YAML frontmatter."""
    skill_path = Path(__file__).parent.parent / "app" / "skills" / "duplicate-detection" / "SKILL.md"
    content = skill_path.read_text()
    assert "name: duplicate-detection" in content


def test_recommendation_skill_has_valid_frontmatter():
    """Recommendation SKILL.md has required YAML frontmatter."""
    skill_path = Path(__file__).parent.parent / "app" / "skills" / "recommendation" / "SKILL.md"
    content = skill_path.read_text()
    assert "name: recommendation" in content


def test_sap_action_mapping_skill_has_valid_frontmatter():
    """SAP action mapping SKILL.md has required YAML frontmatter."""
    skill_path = Path(__file__).parent.parent / "app" / "skills" / "sap-action-mapping" / "SKILL.md"
    content = skill_path.read_text()
    assert "name: sap-action-mapping" in content


def test_sap_action_mapping_skill_contains_all_api_actions():
    """SAP action mapping skill documents all five API actions."""
    skill_path = Path(__file__).parent.parent / "app" / "skills" / "sap-action-mapping" / "SKILL.md"
    content = skill_path.read_text()
    for action in [
        "ApproveMaintWorkRequest",
        "RejectMaintWorkRequest",
        "SetMaintNotifToInfoRequired",
        "SetMaintNotifToInProcess",
        "CompleteMaintNotification",
    ]:
        assert action in content, f"Action '{action}' missing from sap-action-mapping skill"


def test_duplicate_detection_skill_excludes_noco():
    """Duplicate detection skill explicitly excludes NOCO notifications."""
    skill_path = Path(__file__).parent.parent / "app" / "skills" / "duplicate-detection" / "SKILL.md"
    content = skill_path.read_text()
    assert "NOCO" in content


def test_config_file_exists():
    """agent_config.yaml exists at the expected path."""
    config_path = Path(__file__).parent.parent / "app" / "config" / "agent_config.yaml"
    assert config_path.exists(), "agent_config.yaml not found"


def test_mcp_mock_json_exists():
    """mcp-mock.json exists in the asset root."""
    mock_path = Path(__file__).parent.parent / "mcp-mock.json"
    assert mock_path.exists(), "mcp-mock.json not found"


def test_mcp_mock_json_has_three_servers():
    """mcp-mock.json contains entries for all three MCP servers."""
    import json
    mock_path = Path(__file__).parent.parent / "mcp-mock.json"
    data = json.loads(mock_path.read_text())
    assert "servers" in data
    assert len(data["servers"]) == 3
    slugs = list(data["servers"].keys())
    assert any("maintnotif" in s for s in slugs)
    assert any("equipment" in s for s in slugs)
    assert any("functionallocation" in s or "functional" in s for s in slugs)
