"""MCP Client — connects to FastMCP servers via JSON-RPC 2.0 over stdio.

Two operating modes:
  • "stdio"  – spawns each server as a subprocess and communicates over the
               real MCP protocol (JSON-RPC 2.0 messages, proper handshake).
               This is the canonical MCP experience.
  • "direct" – imports the server module in-process and calls the decorated
               tool function directly.  Still uses the FastMCP tool definitions
               (schemas, descriptions, validation) but skips the subprocess.
               Default for Streamlit where latency matters.

Set MCP_TRANSPORT=stdio in .env to enable cross-process mode.

Usage:
    client = MCPClient()
    result = client.call_tool("mcp_marketdata_alpha_vantage",
                              "get_quote", {"symbol": "AAPL"})
"""

from __future__ import annotations

import asyncio
import importlib
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from persistence.database import Database
from schemas.audit import ToolCallRecord

_SERVER_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SERVER_DIR.parent
_PYTHON = sys.executable

SERVER_REGISTRY: dict[str, dict[str, str]] = {
    "mcp_marketdata_alpha_vantage": {
        "script": "alpha_vantage_server.py",
        "module": "mcp_servers.alpha_vantage_server",
    },
    "mcp_macro_fred": {
        "script": "fred_server.py",
        "module": "mcp_servers.fred_server",
    },
    "mcp_filings_sec_edgar": {
        "script": "sec_edgar_server.py",
        "module": "mcp_servers.sec_edgar_server",
    },
    "mcp_news_gdelt": {
        "script": "gdelt_server.py",
        "module": "mcp_servers.gdelt_server",
    },
    "mcp_events_fmp": {
        "script": "fmp_server.py",
        "module": "mcp_servers.fmp_server",
    },
    "mcp_quant": {
        "script": "quant_server.py",
        "module": "mcp_servers.quant_server",
    },
}

_module_cache: dict[str, Any] = {}


def _import_server_module(server_name: str) -> Any:
    """Lazily import and cache a server module for direct-mode calls."""
    if server_name in _module_cache:
        return _module_cache[server_name]
    entry = SERVER_REGISTRY.get(server_name)
    if not entry:
        raise KeyError(f"Unknown MCP server '{server_name}'")
    mod = importlib.import_module(entry["module"])
    _module_cache[server_name] = mod
    return mod


class MCPClient:
    """MCP client with stdio (real protocol) and direct (in-process) modes."""

    def __init__(self, mode: str | None = None, log_calls: bool = True) -> None:
        self.mode = mode or os.getenv("MCP_TRANSPORT", "direct")
        self._log = log_calls
        self._tool_schema_cache: dict[str, list[dict]] = {}

    # ── Public API ────────────────────────────────────────────────────

    def call_tool(self, server_name: str, tool_name: str,
                  arguments: dict[str, Any] | None = None) -> dict:
        """Call a tool. Routes through stdio or direct mode."""
        arguments = arguments or {}
        t0 = time.time()
        error_msg = ""

        try:
            if self.mode == "stdio":
                result = self._call_stdio(server_name, tool_name, arguments)
            else:
                result = self._call_direct(server_name, tool_name, arguments)
        except Exception as exc:
            error_msg = str(exc)
            result = {"error": error_msg}

        latency_ms = (time.time() - t0) * 1000

        if self._log:
            self._audit(server_name, tool_name, arguments, result,
                        latency_ms, not bool(error_msg), error_msg)

        return result

    def list_tools(self, server_name: str) -> list[dict]:
        """Discover tools on a server (via JSON-RPC tools/list)."""
        if server_name in self._tool_schema_cache:
            return self._tool_schema_cache[server_name]

        if self.mode == "stdio":
            tools = self._run_async(self._list_tools_stdio(server_name))
        else:
            tools = self._list_tools_direct(server_name)

        self._tool_schema_cache[server_name] = tools
        return tools

    def list_all_servers(self) -> dict[str, list[dict]]:
        """Discover tools on every registered MCP server."""
        return {name: self.list_tools(name) for name in SERVER_REGISTRY}

    # ── STDIO mode (real MCP protocol) ────────────────────────────────

    def _server_params(self, server_name: str) -> StdioServerParameters:
        entry = SERVER_REGISTRY.get(server_name)
        if not entry:
            raise KeyError(f"Unknown MCP server '{server_name}'")
        env = {**os.environ, "PYTHONPATH": str(_PROJECT_ROOT)}
        return StdioServerParameters(
            command=_PYTHON,
            args=[str(_SERVER_DIR / entry["script"])],
            env=env,
        )

    async def _list_tools_stdio(self, server_name: str) -> list[dict]:
        params = self._server_params(server_name)
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                resp = await session.list_tools()
                return [
                    {"name": t.name,
                     "description": t.description or "",
                     "schema": t.inputSchema if hasattr(t, "inputSchema") else {}}
                    for t in resp.tools
                ]

    async def _call_tool_stdio(self, server_name: str, tool_name: str,
                               arguments: dict) -> dict:
        params = self._server_params(server_name)
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                text_parts = []
                for content in result.content:
                    if hasattr(content, "text"):
                        text_parts.append(content.text)
                raw = "\n".join(text_parts)
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    return {"raw": raw}

    def _call_stdio(self, server_name: str, tool_name: str,
                    arguments: dict) -> dict:
        return self._run_async(
            self._call_tool_stdio(server_name, tool_name, arguments)
        )

    # ── Direct mode (in-process, MCP tool definitions) ────────────────

    def _list_tools_direct(self, server_name: str) -> list[dict]:
        mod = _import_server_module(server_name)
        mcp_app = getattr(mod, "mcp", None)
        if mcp_app is None:
            return []
        tools = []
        for name, fn in mcp_app._tool_manager._tools.items():
            params = fn.parameters
            if hasattr(params, "model_json_schema"):
                schema = params.model_json_schema()
            elif isinstance(params, dict):
                schema = params
            else:
                schema = {}
            tools.append({
                "name": name,
                "description": fn.description or "",
                "schema": schema,
            })
        return tools

    def _call_direct(self, server_name: str, tool_name: str,
                     arguments: dict) -> dict:
        mod = _import_server_module(server_name)
        func = getattr(mod, tool_name, None)
        if func is None:
            raise AttributeError(
                f"Tool '{tool_name}' not found on server '{server_name}'")
        raw = func(**arguments)
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {"raw": raw}
        if isinstance(raw, dict):
            return raw
        return {"result": raw}

    # ── Async helper ──────────────────────────────────────────────────

    @staticmethod
    def _run_async(coro: Any) -> Any:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result(timeout=120)
        return asyncio.run(coro)

    # ── Audit logging ─────────────────────────────────────────────────

    @staticmethod
    def _audit(server: str, tool: str, params: dict, result: dict,
               latency: float, success: bool, error: str) -> None:
        try:
            db = Database()
            record = ToolCallRecord(
                call_id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc),
                server_name=server,
                tool_name=tool,
                parameters=params,
                response_summary=str(result.get("data", result))[:500],
                latency_ms=latency,
                success=success,
                error_message=error,
                cached=False,
            )
            db.log_tool_call(record.model_dump(mode="json"))
        except Exception:
            pass
