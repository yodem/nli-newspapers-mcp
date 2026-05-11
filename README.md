# NLI Newspapers MCP Server

An MCP server for searching and reading the National Library of Israel's historical Jewish newspaper archive. Combines the NLI Search API (for catalog discovery) with JPRESS browser automation (for full-text article search and OCR text retrieval).

**Collection:** 5M+ pages, 25 languages, 240 years of historical Jewish newspapers.

## Quick Start

```bash
# 1. Clone and install
cd nli-newspapers-mcp
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium

# 2. One-time Cloudflare setup (opens Chrome, browse the page, close Chrome)
python -m nli_newspapers_mcp.jpress_client

# 3. Add to Claude Code settings (~/.claude/settings.json)
```

```json
{
  "mcpServers": {
    "nli-newspapers": {
      "command": "/path/to/nli-newspapers-mcp/.venv/bin/python",
      "args": ["-m", "nli_newspapers_mcp.server"],
      "env": {
        "NLI_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

## Tools

| Tool | Source | Description |
|------|--------|-------------|
| `search_newspapers` | NLI API | Search catalog for newspaper titles by subject/keyword |
| `get_newspaper_metadata` | IIIF API | Get detailed metadata for a newspaper by record ID |
| `search_articles` | JPRESS | Full-text search across all newspaper content |
| `list_newspaper_titles` | JPRESS | Browse all 2,200+ newspaper titles with filters |
| `get_newspaper_issues` | JPRESS | List available issues (months) for a newspaper |
| `get_page_text` | JPRESS | Get OCR text for a specific article |

## Architecture

```
Claude Code
    | (MCP stdio)
    v
+---------------------------+
| NLI Newspapers MCP Server |
+---------------------------+
| nli_client (httpx)        |  <-- NLI Search API + IIIF (no Cloudflare)
| jpress_client (Playwright)|  <-- JPRESS Veridian (Cloudflare-protected)
+---------------------------+
```

- **NLI API tools** use httpx directly (Cloudflare does not protect the API)
- **JPRESS tools** use Playwright with saved Cloudflare cookies (see Cloudflare Setup below)

## Cloudflare Setup

JPRESS (www.nli.org.il/he/newspapers) is behind Cloudflare's JavaScript challenge. Automated browsers (Playwright, Selenium) cannot pass it. The workaround:

1. Run the setup command: `python -m nli_newspapers_mcp.jpress_client`
2. This opens real Chrome with a dedicated profile
3. Wait for the JPRESS page to load (Cloudflare passes automatically in real Chrome)
4. Close Chrome
5. Cookies are extracted and saved to `~/.nli-newspapers-mcp/cookies.json`
6. The MCP server injects these cookies into Playwright to bypass Cloudflare

Cookies expire periodically. Re-run the setup when JPRESS tools start failing.

## API Key

Get your NLI API key at: https://api.nli.org.il/signup/

Set it via the `NLI_API_KEY` environment variable.

## Tests

```bash
pytest -v  # 20 tests, all offline (no network needed)
```

## Project Status

See [PROGRESS.md](PROGRESS.md) for detailed build history and decisions.
See [CLAUDE.md](CLAUDE.md) for AI-readable project context.
