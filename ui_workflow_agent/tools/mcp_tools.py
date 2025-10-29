import asyncio
import os
from mcp import ClientSession
from mcp.client.sse import sse_client
from fastmcp import Client
from dotenv import load_dotenv
from logging import getLogger

load_dotenv()

MCP_SERVER = os.getenv("MCP_SERVER_URL", "http://localhost:8080")
client = Client("http://localhost:8080/mcp")

logger = getLogger(__name__)

async def call_mcp_tools(tool_name:str, inputs:dict):
    # SSE server URL
    server_url = f"{MCP_SERVER}/sse"
    print(f"Connecting to SSE server at {server_url}...")
    try:
        # Create the connection via SSE transport
        async with sse_client(url=server_url) as streams:
            # Create the client session with the streams
            async with ClientSession(*streams) as session:
                # Initialize the session
                await session.initialize()
                result = await session.call_tool(tool_name, inputs)
                return result.content
    except Exception as e:
        logger.error(f"Error in create_mcp_session: {e}")
        raise

async def call_browseruse_tool(instructions: str):
    async with client:
        result = await client.call_tool("run_browser_use_tool", {"instructions": instructions})
        logger.info(f"Result from run_browser_use_tool: {result.content[0].text}")
        return result.content[0].text


async def invoke_browser_use_tool(instructions:str):
    """ This tool is used to run the browser use tool."""
    return await call_browseruse_tool(instructions)