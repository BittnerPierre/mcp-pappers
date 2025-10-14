"""Test client for MCP Pappers server using official MCP Python client."""

import argparse
import asyncio
import os
from contextlib import AsyncExitStack

from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client

# Load environment variables
load_dotenv()


async def test_get_company_details(transport: str = "sse"):
    """Test the get_company_details tool with SIREN 443061841 (Google France).

    Args:
        transport: Transport type to use ("sse" or "streamable-http")
    """

    # Get API key from environment if set
    api_key = os.getenv("MCP_API_KEY")

    print("🔍 Testing MCP Pappers Server")
    print("📍 URL: https://mcp-pappers-08aa3f2c.alpic.live")
    print(f"🔌 Transport: {transport}")
    print(f"🔑 Authentication: {'Enabled (x-api-key)' if api_key else 'Disabled (public mode)'}")
    print("🏢 SIREN: 443061841 (Google France)")
    print("\n" + "="*60 + "\n")

    # Connect to the MCP server
    server_url = "https://mcp-pappers-08aa3f2c.alpic.live"

    # Prepare headers with API key if available
    headers = {"x-api-key": api_key} if api_key else {}

    async with AsyncExitStack() as stack:
        # Create client connection based on transport type
        if transport == "streamable-http":
            read_stream, write_stream = await stack.enter_async_context(
                streamablehttp_client(server_url, headers=headers)
            )
        else:  # sse
            read_stream, write_stream = await stack.enter_async_context(
                sse_client(server_url, headers=headers)
            )

        # Create client session
        session = await stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )

        # Initialize the session
        await session.initialize()
        print("✅ Connected to MCP server\n")

        # List available tools
        tools_result = await session.list_tools()
        print("📋 Available tools:")
        for tool in tools_result.tools:
            print(f"  - {tool.name}: {tool.description}")
        print()

        # Call the get_company_details tool
        print("🔧 Calling get_company_details(siren='443061841')...")
        result = await session.call_tool(
            "get_company_details",
            arguments={"siren": "443061841"}
        )

        print("\n✅ Success!")
        print("\n" + "="*60)
        print("Response:")
        print("="*60 + "\n")
        for content in result.content:
            if hasattr(content, 'text'):
                print(content.text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test MCP Pappers Server")
    parser.add_argument(
        "--transport",
        "-t",
        choices=["sse", "streamable-http"],
        default="sse",
        help="Transport type to use (default: sse)",
    )
    args = parser.parse_args()

    asyncio.run(test_get_company_details(transport=args.transport))
