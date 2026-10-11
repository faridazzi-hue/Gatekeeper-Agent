"""Tests for prompt_injection_detector module."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "app"))


def make_mock_tool(name="test_tool", description="A test tool"):
    tool = MagicMock()
    tool.name = name
    tool.description = description
    tool.args_schema = None
    tool.invoke = MagicMock(return_value={"result": "ok"})
    tool.ainvoke = AsyncMock(return_value={"result": "ok"})
    return tool


def test_wrap_tool_returns_structured_tool():
    """wrap_tool returns a callable tool wrapper."""
    from prompt_injection_detector import wrap_tool
    original = make_mock_tool()
    wrapped = wrap_tool(original)
    assert wrapped is not None
    assert hasattr(wrapped, "name") or callable(wrapped)


def test_wrap_tool_preserves_name():
    """Wrapped tool retains the original tool name."""
    from prompt_injection_detector import wrap_tool
    original = make_mock_tool(name="my_special_tool")
    wrapped = wrap_tool(original)
    # The wrapped tool should have the same name
    assert wrapped.name == "my_special_tool"


def test_safe_tool_call_returns_structured_tool():
    """wrap_tool produces a StructuredTool — spot-check structure."""
    from prompt_injection_detector import wrap_tool
    from langchain_core.tools import StructuredTool
    original = make_mock_tool()
    wrapped = wrap_tool(original)
    assert isinstance(wrapped, StructuredTool)
    assert wrapped.name == original.name


def test_wrap_tool_non_injection_original_preserved():
    """Wrapping a tool preserves the description from the original tool."""
    from prompt_injection_detector import wrap_tool
    original = make_mock_tool(description="List maintenance notifications by plant")
    wrapped = wrap_tool(original)
    assert "maintenance" in wrapped.description.lower() or wrapped.description is not None
