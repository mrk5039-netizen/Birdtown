"""Live integration wiring via the Anthropic remote-MCP connector.

The agent has two layers of tools:

  * **Local `@beta_tool` functions** (`tools.py`) — the policy brain. Scoring,
    compliance validation, and CRM bookkeeping run here, in code we control.
  * **Remote MCP servers** (this module) — the real I/O. ZoomInfo, Gmail,
    Google Calendar, Slack, and Notion are reached through Anthropic's
    `mcp_servers` connector, so Claude calls their tools directly and the
    provider executes them server-side.

Configuration is env-driven so nothing is hardcoded. Point `SDR_MCP_CONFIG` at
a JSON file (see `mcp_servers.example.json`) listing the servers to connect:

    [
      {"name": "zoominfo", "url": "https://mcp.zoominfo.com/...",
       "authorization_token_env": "ZOOMINFO_MCP_TOKEN"},
      {"name": "gmail",    "url": "https://mcp.gmail.example/...",
       "authorization_token_env": "GMAIL_MCP_TOKEN"}
    ]

If no config is present, the agent runs purely on the local stub tools — which
is exactly the safe default for development.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

# Beta header required to use the remote MCP connector on the Messages API.
MCP_CONNECTOR_BETA = "mcp-client-2025-04-04"


def load_mcp_servers() -> list[dict]:
    """Build the `mcp_servers` payload from `SDR_MCP_CONFIG`.

    Returns an empty list when no config is set, so the agent transparently
    falls back to local-only tools. Auth tokens are resolved from the
    environment (via each entry's `authorization_token_env`) and never read
    from the config file itself.
    """
    cfg_path = os.getenv("SDR_MCP_CONFIG")
    if not cfg_path:
        return []

    path = Path(cfg_path).expanduser()
    if not path.is_file():
        raise RuntimeError(f"SDR_MCP_CONFIG points to a missing file: {path}")

    entries = json.loads(path.read_text())
    servers: list[dict] = []
    for entry in entries:
        server: dict = {
            "type": "url",
            "url": entry["url"],
            "name": entry["name"],
        }
        # Resolve the bearer token from the named env var, if any.
        token_env = entry.get("authorization_token_env")
        if token_env:
            token = os.getenv(token_env)
            if not token:
                raise RuntimeError(
                    f"MCP server '{entry['name']}' expects token in ${token_env}, "
                    "but it is not set."
                )
            server["authorization_token"] = token
        # Optional: restrict which of the server's tools the agent may call.
        if "allowed_tools" in entry:
            server["tool_configuration"] = {
                "enabled": True,
                "allowed_tools": entry["allowed_tools"],
            }
        servers.append(server)
    return servers


def connected_server_names(servers: list[dict]) -> list[str]:
    """Names of the live MCP servers, for the system prompt and logging."""
    return [s["name"] for s in servers]
