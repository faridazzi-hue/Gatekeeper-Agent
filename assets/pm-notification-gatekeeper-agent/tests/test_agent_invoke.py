"""Integration test — full agent invoke flow with mocked LLM and MCP tools."""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "app"))


def make_mock_tool(name: str):
    """Create a minimal mock LangChain tool."""
    tool = MagicMock()
    tool.name = name
    tool.description = f"Mock tool: {name}"
    return tool


def make_mock_llm_response(content: str):
    """Create a mock LLM final message."""
    msg = MagicMock()
    msg.content = content
    return msg


@pytest.mark.asyncio
async def test_agent_invoke_returns_completed_status():
    """Agent invoke returns completed status with a non-empty message."""
    mock_tools = [
        make_mock_tool("list_maintenancenotification_for_cds_api_maintnotification"),
        make_mock_tool("get_equipment_for_cds_api_equipment"),
        make_mock_tool("get_functionallocation_for_cds_api_functionallocation"),
    ]

    mock_response_content = (
        "I can help you review maintenance notifications. "
        "Please provide your plant identifier to proceed."
    )

    with patch("mcp_tools.get_mcp_tools", new_callable=AsyncMock) as mock_get_tools, \
         patch("agent.ChatLiteLLM") as mock_llm_class:

        mock_get_tools.return_value = mock_tools

        # Mock LLM to return a final answer
        mock_llm_instance = MagicMock()
        mock_llm_class.return_value = mock_llm_instance

        # Simulate the graph ainvoke returning a final message
        final_msg = make_mock_llm_response(mock_response_content)
        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {"messages": [final_msg]}

        from agent import SampleAgent
        agent = SampleAgent()

        with patch.object(agent, "_create_graph", return_value=mock_graph), \
             patch.object(agent, "_invoke_with_fallback", new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = {"messages": [final_msg]}

            result = await agent.invoke(
                "Show me pending notifications for plant 1710",
                context_id="test-session-001",
                tools=mock_tools,
            )

    assert result.status == "completed"
    assert len(result.message) > 0


@pytest.mark.asyncio
async def test_agent_stream_yields_processing_then_result():
    """Agent stream yields at least two items: a working status and a completion."""
    mock_tools = [make_mock_tool("list_maintenancenotification_for_cds_api_maintnotification")]
    final_msg = make_mock_llm_response("Please provide your plant identifier.")

    from agent import SampleAgent
    agent = SampleAgent()

    with patch.object(agent, "_invoke_with_fallback", new_callable=AsyncMock) as mock_invoke:
        mock_invoke.return_value = {"messages": [final_msg]}

        items = []
        async for item in agent.stream(
            "List pending notifications", "test-session-002", tools=mock_tools
        ):
            items.append(item)

    assert len(items) >= 2
    # First item is the "Processing..." status
    assert items[0]["is_task_complete"] is False
    assert items[0]["require_user_input"] is False
    # Last item should be complete
    last = items[-1]
    assert last["is_task_complete"] is True


@pytest.mark.asyncio
async def test_agent_handles_invoke_failure_gracefully():
    """Agent stream returns error status when invocation throws."""
    from agent import SampleAgent
    agent = SampleAgent()

    with patch.object(agent, "_invoke_with_fallback", side_effect=RuntimeError("LLM unavailable")):
        items = []
        async for item in agent.stream("test query", "test-session-003", tools=[]):
            items.append(item)

    last = items[-1]
    assert last["is_task_complete"] is True
    assert "error" in last["content"].lower() or "encountered" in last["content"].lower()
