"""MCP connection factory.

Supports both streamable-http and SSE transport types.
"""

from google.adk.tools.mcp_tool import (
    McpToolset,
    StreamableHTTPConnectionParams,
    SseConnectionParams,
)


def get_mcp_connection(mcp_config) -> McpToolset:
    """Create an MCP toolset from a Dynaconf config section.

    Args:
        mcp_config: Config object with .transport, .url, and optional .headers

    Returns:
        McpToolset configured for the given transport type.

    Raises:
        ValueError: If transport type is not supported.
    """
    transport = getattr(mcp_config, "transport", "streamable-http")
    url = mcp_config.url
    headers = getattr(mcp_config, "headers", {})

    # Convert Dynaconf Box to plain dict if needed
    if hasattr(headers, "to_dict"):
        headers = headers.to_dict()

    if transport == "streamable-http":
        connection_params = StreamableHTTPConnectionParams(
            url=url,
            headers=headers,
        )
    elif transport == "sse":
        connection_params = SseConnectionParams(
            url=url,
            headers=headers,
        )
    else:
        raise ValueError(
            f"Unsupported MCP transport type: '{transport}'. "
            f"Expected 'streamable-http' or 'sse'."
        )

    return McpToolset(connection_params=connection_params)
