"""MCP utility for managing client connections."""

import json
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


@asynccontextmanager
async def get_mcp_client(
    command: Optional[str] = None, args: Optional[list[str]] = None, url: Optional[str] = None
) -> AsyncGenerator[Optional[ClientSession], None]:
    """
    Connect to an MCP server and yield a session.

    Args:
        command: Command to run (for stdio)
        args: Command arguments (for stdio)
        url: Server URL (for SSE - not yet implemented)

    Yields:
        Initialized ClientSession or None
    """
    if not command and not url:
        yield None
        return

    try:
        if command:
            # Handle string JSON args if they come from .env
            processed_args = args or []
            if isinstance(processed_args, str):
                try:
                    processed_args = json.loads(processed_args)
                except json.JSONDecodeError:
                    processed_args = [processed_args]

            server_params = StdioServerParameters(
                command=command,
                args=processed_args,
            )

            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    logger.info(f"Initialized MCP connection via stdio: {command}")
                    yield session
        else:
            # SSE support could be added here
            logger.warning("SSE MCP support not yet implemented")
            yield None

    except Exception as e:
        logger.error(f"Failed to initialize MCP client: {e}")
        yield None
