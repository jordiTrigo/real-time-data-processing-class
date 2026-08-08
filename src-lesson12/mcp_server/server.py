"""A small adapter and optional runnable MCP SDK server.

Keeping this protocol-neutral makes the lesson runnable before students install an
MCP package.  The methods match MCP's discover-tools/call-tool shape and return
JSON-safe dictionaries.
"""

from __future__ import annotations

from typing import Any

from agent.tools import Lesson12Diagnostics, ToolCatalog


class IncidentMCPServer:
    def __init__(self, diagnostics: ToolCatalog) -> None:
        self.diagnostics = diagnostics

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": name,
                "description": "Read-only Lesson 12 incident diagnostic.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            }
            for name in self.diagnostics.names()
        ]

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        if arguments:
            return {
                "isError": True,
                "content": [{"type": "text", "text": "This tool takes no arguments."}],
            }
        result = self.diagnostics.invoke(name)
        return {
            "isError": not result.succeeded,
            "content": [{"type": "text", "text": result.raw or result.summary}],
            "structuredContent": {
                "tool_name": result.tool_name,
                "succeeded": result.succeeded,
                "summary": result.summary,
            },
        }


def create_mcp_server(diagnostics: ToolCatalog | None = None) -> Any:
    """Create a runnable MCP server for SDK v2, with FastMCP v1 compatibility."""

    try:
        from mcp.server import MCPServer
    except ImportError as error:  # pragma: no cover - optional classroom extra
        try:
            from mcp.server.fastmcp import FastMCP
        except ImportError:
            raise RuntimeError(
                "Install the optional 'mcp' package to run the MCP stdio server."
            ) from error
        server_class = FastMCP
    else:
        server_class = MCPServer
    bridge = IncidentMCPServer(diagnostics or Lesson12Diagnostics())
    server = server_class("lesson12-incident-diagnostics")

    for tool in bridge.list_tools():
        invoke_tool = _mcp_callable(bridge, tool["name"], tool["description"])
        server.tool(name=tool["name"], description=tool["description"])(invoke_tool)
    return server


# Kept as an import-compatible alias for older teaching notebooks.
create_fastmcp = create_mcp_server


def _mcp_callable(bridge: IncidentMCPServer, name: str, description: str) -> Any:
    """Create a no-argument callable, so the SDK publishes an empty input schema."""

    def invoke_tool() -> dict[str, Any]:
        return bridge.call_tool(name)

    invoke_tool.__name__ = name
    invoke_tool.__doc__ = description
    return invoke_tool


def main() -> None:
    """Start an MCP stdio server: ``python -m mcp_server.server``."""

    create_mcp_server().run()


if __name__ == "__main__":
    main()
