from __future__ import annotations
import os
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from nli_newspapers_mcp.nli_client import NLIClient
from nli_newspapers_mcp.jpress_client import JpressClient

server = Server("nli-newspapers")
nli: NLIClient | None = None
jpress: JpressClient | None = None


def _get_nli() -> NLIClient:
    global nli
    if nli is None:
        api_key = os.environ.get("NLI_API_KEY", "")
        if not api_key:
            raise ValueError("NLI_API_KEY environment variable is required")
        nli = NLIClient(api_key=api_key)
    return nli


def _get_jpress() -> JpressClient:
    global jpress
    if jpress is None:
        jpress = JpressClient()
    return jpress


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_newspapers",
            description="Search the NLI catalog for newspaper titles by subject, title, or keyword. Returns catalog metadata.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "language": {"type": "string", "description": "ISO 639-3 code (heb, eng, yid)"},
                    "max_results": {"type": "integer", "default": 10},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_newspaper_metadata",
            description="Get detailed metadata for a newspaper from its NLI record ID (from search_newspapers results).",
            inputSchema={
                "type": "object",
                "properties": {
                    "record_id": {"type": "string", "description": "NLI record ID"},
                },
                "required": ["record_id"],
            },
        ),
        Tool(
            name="search_articles",
            description="Full-text search across JPRESS historical newspaper content. Supports exact phrases, boolean operators (AND/OR/NOT), wildcards (?/*), fuzzy (~1), proximity search.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "newspaper": {"type": "string", "description": "Limit to newspaper pub_code"},
                    "max_results": {"type": "integer", "default": 20},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="list_newspaper_titles",
            description="Browse all available JPRESS newspaper titles. Filter by language or region.",
            inputSchema={
                "type": "object",
                "properties": {
                    "language": {"type": "string", "description": "Filter by language name (e.g. עברית, אנגלית)"},
                    "region": {"type": "string", "description": "Filter by region"},
                },
            },
        ),
        Tool(
            name="get_newspaper_issues",
            description="Get available issues (month-level) for a specific newspaper by pub_code.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pub_code": {"type": "string", "description": "Newspaper publication code"},
                    "year": {"type": "integer", "description": "Filter to year"},
                },
                "required": ["pub_code"],
            },
        ),
        Tool(
            name="get_page_text",
            description="Get OCR text for a specific newspaper article/page URL (from search_articles or get_newspaper_issues results).",
            inputSchema={
                "type": "object",
                "properties": {
                    "page_url": {"type": "string", "description": "Article or page URL"},
                },
                "required": ["page_url"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "search_newspapers":
            client = _get_nli()
            results = await client.search_newspapers(
                query=arguments["query"],
                language=arguments.get("language"),
                max_results=arguments.get("max_results", 10),
            )
            return [TextContent(type="text", text=json.dumps(
                [r.model_dump() for r in results], ensure_ascii=False, indent=2
            ))]

        elif name == "get_newspaper_metadata":
            client = _get_nli()
            meta = await client.get_newspaper_metadata(arguments["record_id"])
            return [TextContent(type="text", text=json.dumps(
                meta.model_dump(), ensure_ascii=False, indent=2
            ))]

        elif name == "search_articles":
            client = _get_jpress()
            results = await client.search_articles(
                query=arguments["query"],
                newspaper=arguments.get("newspaper"),
                max_results=arguments.get("max_results", 20),
            )
            return [TextContent(type="text", text=json.dumps(
                [r.model_dump() for r in results], ensure_ascii=False, indent=2
            ))]

        elif name == "list_newspaper_titles":
            client = _get_jpress()
            titles = await client.list_titles(
                language=arguments.get("language"),
                region=arguments.get("region"),
            )
            return [TextContent(type="text", text=json.dumps(
                [t.model_dump() for t in titles], ensure_ascii=False, indent=2
            ))]

        elif name == "get_newspaper_issues":
            client = _get_jpress()
            issues = await client.get_issues(
                pub_code=arguments["pub_code"],
                year=arguments.get("year"),
            )
            return [TextContent(type="text", text=json.dumps(
                [i.model_dump() for i in issues], ensure_ascii=False, indent=2
            ))]

        elif name == "get_page_text":
            client = _get_jpress()
            page = await client.get_page_text(arguments["page_url"])
            return [TextContent(type="text", text=json.dumps(
                page.model_dump(), ensure_ascii=False, indent=2
            ))]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {e}")]


async def run():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main():
    import asyncio
    asyncio.run(run())


if __name__ == "__main__":
    main()
