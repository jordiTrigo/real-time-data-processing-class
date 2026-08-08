from __future__ import annotations

import unittest

from agent.resources import LexicalRunbookRetriever
from agent.tools import FixtureDiagnostics, ToolResult
from mcp_server.server import IncidentMCPServer, create_mcp_server


class AgentResourceTests(unittest.TestCase):
    def test_lexical_retrieval_returns_relevant_local_guidance(self) -> None:
        result = LexicalRunbookRetriever().render("inactive replication slot retains WAL")
        self.assertIn("replication-slot", result)
        self.assertIn("retrieved guidance", result)

    def test_mcp_bridge_is_read_only_and_json_shaped(self) -> None:
        bridge = IncidentMCPServer(
            FixtureDiagnostics(
                {"runbook_context": ToolResult("runbook_context", True, "ok", "guide")}
            )
        )
        self.assertEqual(bridge.list_tools()[0]["name"], "runbook_context")
        response = bridge.call_tool("runbook_context")
        self.assertFalse(response["isError"])
        self.assertEqual(response["structuredContent"]["tool_name"], "runbook_context")

    def test_installed_mcp_sdk_builds_a_runnable_server(self) -> None:
        server = create_mcp_server(
            FixtureDiagnostics(
                {"runbook_context": ToolResult("runbook_context", True, "ok", "guide")}
            )
        )
        self.assertIn(type(server).__name__, {"MCPServer", "FastMCP"})
