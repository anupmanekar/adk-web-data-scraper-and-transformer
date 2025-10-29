import asyncio
import os
from fastmcp import Client
from dotenv import load_dotenv
from logging import getLogger

load_dotenv()

logger = getLogger(__name__)

config = {
    "mcpServers": {
    "chrome-devtools": {
        "command": "npx",
        "args": ["-y", "chrome-devtools-mcp@latest"]
    }
  }
}

# Create a client that connects to all servers
client = Client(config)

async def main():
    async with client:
        # Access tools and resources with server prefixes
        result = await client.call_tool("navigate_page", {"url": "https://www.example.com"})
        print(result)

async def navigate_to_url(url: str):
    async with client:
        result = await client.call_tool("navigate_page", {"url": url})
        print(result)

async def fill_input(uid: str, value: str):
    async with client:
        await client.call_tool("take_snapshot")
        result = await client.call_tool("fill", {"uid": uid, "value": value})
        print(result)

async def click(uid: str):
    async with client:
        await client.call_tool("take_snapshot")
        result = await client.call_tool("click", {"uid": uid})
        print(result)

async def search_and_click(url: str, uid: str, value: str):
    async with client:
        result = await client.call_tool("navigate_page", {"url": url})
        print(result)
        result = await client.call_tool("fill", {"uid": uid, "value": value})
        print(result)
        result = await client.call_tool("click", {"uid": uid})
        print(result)

