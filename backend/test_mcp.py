
import asyncio
from fastmcp import Client
from backend.mcp_server import mcp


async def main():
    async with Client(mcp) as client:
        result = await client.call_tool(
            "search_opportunities",
            {"category": "hackathon"}
        )

        print("ORBIT MCP TOOL RESULT:")
        print(result.data)


if __name__ == "__main__":
    asyncio.run(main())
