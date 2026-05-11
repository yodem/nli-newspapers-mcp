# NLI Newspapers MCP Server

## What This Is

An MCP server providing programmatic access to the National Library of Israel's historical Jewish newspaper archive (JPRESS). Built as a hybrid: NLI REST API for catalog discovery, Playwright browser automation for JPRESS content access.

## Project Structure

```
src/nli_newspapers_mcp/
  server.py          -- MCP server entry point. 6 tools defined via @server.list_tools / @server.call_tool.
  nli_client.py      -- NLIClient class. httpx async client for NLI Search API + IIIF manifests.
  jpress_client.py   -- JpressParser (static HTML parsing) + JpressClient (Playwright browser). Also has setup_browser_profile() for Cloudflare cookie setup.
  models.py          -- Pydantic models: NewspaperRecord, NewspaperMetadata, ArticleResult, NewspaperTitle, IssueInfo, PageText.

tests/
  test_models.py          -- Model creation and from_* classmethod tests
  test_nli_client.py      -- NLI API tests using respx mocks
  test_jpress_parsing.py  -- HTML parsing tests against saved fixture files
  test_server.py          -- MCP server integration tests
  fixtures/               -- Saved HTML/JSON from live services (used for offline tests)
```

## Key Technical Decisions

### Two Data Sources

The NLI has two separate systems for newspapers:
- **NLI Search API** (api.nli.org.il): Has catalog records for newspapers as `material_type=periodical`. Returns metadata (title, language, publisher, subjects). The `material_type=NEWSPAPER` option exists but is non-functional (empty results, invalid field errors).
- **JPRESS** (www.nli.org.il/he/newspapers): Veridian platform with actual content. Full-text OCR search, page images, article text. No REST API -- web interface only.

### Cloudflare is the Hard Constraint

JPRESS is behind Cloudflare's JavaScript challenge. Every automated approach was tested:
- curl/httpx with browser headers: 403
- Playwright headless Chromium: stuck on challenge
- Playwright headed Chromium: stuck on challenge
- Playwright Firefox: stuck on challenge
- Playwright with Chrome channel: stuck on challenge
- Persistent context: stuck on challenge
- CDP connection to existing browser: stuck on challenge
- Anti-detection flags: stuck on challenge

**Only real Chrome** (not Playwright-controlled) passes the challenge. The solution: user runs Chrome once manually, we extract cookies from Chrome's SQLite database, inject them into Playwright's browser context.

Cookies are saved to `~/.nli-newspapers-mcp/cookies.json`. They expire periodically and need re-extraction.

### HTML Parsing Specifics

JPRESS uses the Veridian platform. Key selectors and patterns:
- **Titles**: `div.nli-title-browser-row` with child divs classed `tt`, `la`, `re`, `co`, `af`, `at`
- **Search results**: `div.vlistentrymaincell` with article link + newspaper info div
- **Article text**: `#documentdisplayleftpanesectiontextcontainer` (load article URL directly, text is in page HTML)
- **Issues**: Month-level links at `/newspapers/{pub_code}/{year}/{month}`
- **All HTML from Playwright** needs `html.replace('\\"', '"')` preprocessing (Playwright serializes with escaped quotes)
- **Unicode bidi markers** (U+2068, U+2069) must be stripped from all extracted text

### NLI API Query Format

Working query for newspaper discovery:
```
GET https://api.nli.org.il/openlibrary/search
  ?api_key={KEY}
  &query=subject,contains,Hebrew newspapers
  &material_type=periodical
  &output_format=json
```

Query format: `field,operator,value,AND;field2,operator2,value2,...`
Operators: `contains`, `exact`
Fields for periodicals: title, creator, subject, publisher, language, start_date, end_date

IIIF manifests: `https://iiif.nli.org.il/IIIFv21/{recordId}/manifest` -- returns metadata but 0 page sequences for newspapers.

### JPRESS URL Patterns

| Action | Pattern |
|--------|---------|
| Titles | `/he/newspapers/titles` |
| Search | `/he/newspapers/?a=q&hs=1&r=1&results=1&txq={query}&ssnip=img&e=-------he-20--1--img-txIN\|txTI--------------1` |
| Newspaper | `/he/newspapers/{pub_code}` |
| Month | `/he/newspapers/{pub_code}/{year}/{month}` |
| Issue | `/he/newspapers/{pub_code}/{year}/{month}/{day}/{issue_num}/` |
| Article | `/he/newspapers/{pub_code}/{year}/{month}/{day}/{issue_num}/article/{article_num}/` |

Search form fields: `txq` (query), `ssnip` (snippet type: img/txt), `puq` (limit to pub_code), `dafyq`/`datyq` (date range).

## Running

```bash
# Tests (all offline)
.venv/bin/pytest -v

# Cloudflare setup (one-time, opens real Chrome)
.venv/bin/python -m nli_newspapers_mcp.jpress_client

# MCP server
NLI_API_KEY=... .venv/bin/python -m nli_newspapers_mcp.server
```

## What Needs Work

See PROGRESS.md for the full status and open items.
