"""Call the real MCP subprocess and compare its output with the HTTP API."""

import argparse
import asyncio
from datetime import timedelta
import json
from pathlib import Path
import sys
from urllib.parse import urlencode
from urllib.request import urlopen

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

DAY = "2099-10-12"


def get_json(api_url, endpoint, params):
    with urlopen(api_url.rstrip("/") + endpoint + "?" + urlencode(params)) as response:
        return json.load(response)


async def verify(api_url):
    before = get_json(api_url, "/bookings", {"date": DAY})
    params = {"date": DAY, "duration_minutes": 60, "room_id": 103}
    expected = get_json(api_url, "/free-slots", params)
    server = StdioServerParameters(
        command=sys.executable,
        args=[str(Path(__file__).with_name("server.py").resolve())],
        env={"ROOMBOOK_API_URL": api_url},
    )
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            assert [tool.name for tool in tools.tools] == ["find_free_slots"]
            assert tools.tools[0].annotations.readOnlyHint
            good = await session.call_tool(
                "find_free_slots", params, read_timeout_seconds=timedelta(seconds=10)
            )
            assert not good.isError, good
            assert good.structuredContent == {
                "count": len(expected), "slots": expected,
            }
            bad = await session.call_tool(
                "find_free_slots", params | {"duration_minutes": 0},
                read_timeout_seconds=timedelta(seconds=10),
            )
            assert bad.isError, bad
            error = "\n".join(item.text for item in bad.content if item.type == "text")
            assert "422" in error and "duration_minutes" in error
    assert get_json(api_url, "/bookings", {"date": DAY}) == before
    return {
        "tool": "find_free_slots", "transport": "stdio",
        "success": {
            "arguments": params, "isError": good.isError,
            "count": len(expected), "first_slots": expected[:2],
            "matches_http_api": True,
        },
        "invalid_input": {
            "arguments": params | {"duration_minutes": 0},
            "isError": bad.isError, "message": error,
        },
        "bookings_unchanged": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default="http://127.0.0.1:8765")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = asyncio.run(verify(args.api_url))
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    print("PASS: MCP success, invalid input, API parity, unchanged bookings")


if __name__ == "__main__":
    main()
