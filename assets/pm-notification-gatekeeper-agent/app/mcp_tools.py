"""MCP tool loading indirection layer.

This module is the owned interface for loading MCP tools into the agent.
Import from here — never directly from sap_cloud_sdk.agentgateway or
mcp_providers.agw — so tests can patch this single entry point.

In production: delegates to the Agent Gateway MCP provider.
In tests (IBD_TESTING=1): the conftest.py patches get_mcp_tools here so
the agent runs with mock tool results from mcp-mock.json without any
network calls or changes to application code.
"""

from mcp_providers.agw import get_mcp_tools  # noqa: F401 — re-exported for patching

__all__ = ["get_mcp_tools"]
