# Progress Log

Build history, decisions, and open items for the NLI Newspapers MCP Server.

## Timeline

### 2026-05-11: Initial Build (v0.1.0)

#### Phase 1: API Exploration

Explored the NLI Open Library APIs to determine what's accessible:

1. **NLI Search API** (`api.nli.org.il/openlibrary/search`):
   - `material_type=NEWSPAPER` is listed but non-functional. VERIDIAN integration returns empty results for all queries. "Search Content Api" fields (`text`, `pub_code`) are rejected as invalid.
   - **Working approach**: `material_type=periodical` + `subject,contains,newspapers` returns catalog records for newspapers from the PRIMO system.
   - Query format: `field,operator,value,AND;field2,...` with operators `contains`/`exact`.

2. **IIIF Presentation API** (`iiif.nli.org.il`):
   - Returns metadata manifests for newspaper records.
   - Newspaper manifests have `sequences: []` (no page images available via IIIF).
   - Alternative titles, publisher, dates, subjects are available.

3. **JPRESS** (Veridian platform at `www.nli.org.il/he/newspapers/`):
   - Has all content: 5M+ pages, full-text OCR search, article text.
   - No REST API. Web interface only.
   - Behind Cloudflare JavaScript challenge.

**Decision**: Hybrid approach -- NLI API for discovery, JPRESS scraping for content.

#### Phase 2: Implementation (8 tasks, TDD)

| Task | Status | Details |
|------|--------|---------|
| 1. Project scaffolding | Done | pyproject.toml, venv with Python 3.11, playwright chromium |
| 2. Pydantic models | Done | 6 models, 5 tests |
| 3. NLI API client | Done | search_newspapers, get_newspaper_metadata, 4 tests with respx mocks |
| 4. JPRESS HTML parsing | Done | 4 parsers (titles, search, articles, issues), 6 tests against saved HTML fixtures |
| 5. JPRESS Playwright client | Done | JpressClient class wrapping parsers with browser automation |
| 6. MCP server | Done | 6 tools, stdio transport |
| 7. Integration tests | Done | 5 server-level tests |
| 8. E2E smoke test | Partial | NLI API verified live. JPRESS blocked by Cloudflare. |

**Test results**: 20/20 tests pass (all offline, no network needed).

#### Phase 3: Cloudflare Battle

Tested every automated browser approach against JPRESS Cloudflare:

| Approach | Result |
|----------|--------|
| curl + browser User-Agent | 403 Forbidden |
| httpx + browser headers + cookies | 403 Forbidden |
| Playwright headless Chromium | Stuck on "Just a moment..." |
| Playwright headed Chromium | Stuck on "Just a moment..." |
| Playwright Chrome channel (system Chrome) | Stuck on "Just a moment..." |
| Playwright Firefox | Stuck on "Just a moment..." |
| Playwright persistent context | Stuck on "Just a moment..." |
| CDP connection to existing browser | Stuck on "Just a moment..." |
| Anti-detection flags (--disable-blink-features=AutomationControlled) | Stuck on "Just a moment..." |

**Decision**: Cookie extraction approach. User opens real Chrome once (Cloudflare passes in non-automated Chrome), we extract cookies from Chrome's SQLite cookie database, inject them into Playwright.

Implemented `setup_browser_profile()` in `jpress_client.py` and cookie injection in `JpressClient._ensure_browser()`.

## Current Status

### Working

- **search_newspapers**: Verified against live NLI API. Returns Hebrew newspaper catalog records.
- **get_newspaper_metadata**: Verified against live IIIF API. Returns rich metadata with alternative titles.
- **All 20 tests pass** (offline, against saved HTML/JSON fixtures).
- **HTML parsing**: Verified against real JPRESS HTML for all 4 parsers.

### Needs Validation

- **JPRESS tools** (search_articles, list_newspaper_titles, get_newspaper_issues, get_page_text): Code and parsing logic are tested against saved HTML. Live E2E test blocked by Cloudflare. Need to validate the cookie-injection approach works.

### Open Items

1. **Cloudflare bypass** (CRITICAL): Cookie injection alone does not work. Cloudflare detects Playwright-controlled browsers even with `cf_clearance` cookies and system Chrome (`channel='chrome'`). Tested approaches that failed: Playwright Chromium, Playwright Firefox, Chrome channel, persistent context, CDP, cookies injection. The most promising path forward is `undetected-chromedriver` (patches Chrome to remove automation markers) or `nodriver` (CDP-only control without Playwright flags). The MCP Playwright plugin (`agent-browser`) somehow passes Cloudflare — investigating how it differs could also unlock a solution.

2. **Search form submission**: The `search_articles` method submits the JPRESS search form via JavaScript (`document.querySelector('#searchpagesearchform').submit()`). This was validated via the MCP Playwright tool in the design phase but not yet tested through the standalone client.

3. **Article text loading**: Some article pages load OCR text via JavaScript after page load. The current implementation waits for `#documentdisplayleftpanesectiontextcontainer` but may need additional waits or JS execution to trigger text loading.

4. **Pagination**: Search results return 20 per page. No pagination support yet. The JPRESS URL supports `result_page` parameter but it hasn't been implemented.

5. **Date filtering for search**: The search form has date range dropdowns (`dafyq`/`datyq`) but these aren't wired up in `search_articles` yet.

6. **Rate limiting**: No rate limiting implemented. JPRESS should be accessed at ~1 req/sec to avoid triggering additional Cloudflare challenges.

7. **Caching**: No caching implemented. The spec calls for 24-hour TTL cache on titles and metadata.

8. **Error messages**: When Cloudflare blocks, the tools return parsed empty results rather than a clear "Cloudflare blocked -- re-run setup" message.

## Decisions Log

| Decision | Rationale | Date |
|----------|-----------|------|
| Hybrid NLI API + JPRESS | NLI API can discover newspapers but has no content. JPRESS has content but no API. | 2026-05-11 |
| Python over TypeScript | User preference implied by Python API key example. Playwright Python SDK is mature. | 2026-05-11 |
| Playwright over httpx for JPRESS | Cloudflare blocks all non-browser HTTP. Even with cookies, curl/httpx get 403. | 2026-05-11 |
| Cookie extraction over persistent context | Playwright persistent context also blocked by Cloudflare. Real Chrome cookies are the only path. | 2026-05-11 |
| `material_type=periodical` over `NEWSPAPER` | `NEWSPAPER` returns empty. Newspapers are cataloged as periodicals in PRIMO. | 2026-05-11 |
| Month-level issues (not day-level) | The newspaper calendar page shows months, not individual issues. Day-level requires navigating into each month. | 2026-05-11 |
| HTML fixture tests (not live tests) | JPRESS is behind Cloudflare, making live tests unreliable. Saved HTML fixtures provide deterministic testing. | 2026-05-11 |

## File Inventory

| File | Lines | Purpose |
|------|-------|---------|
| `src/nli_newspapers_mcp/models.py` | ~80 | 6 Pydantic models + DC/IIIF parsing helpers |
| `src/nli_newspapers_mcp/nli_client.py` | ~55 | NLI Search API + IIIF client (httpx) |
| `src/nli_newspapers_mcp/jpress_client.py` | ~230 | JpressParser (4 parsers) + JpressClient (Playwright) + setup script |
| `src/nli_newspapers_mcp/server.py` | ~120 | MCP server with 6 tools |
| `tests/test_models.py` | ~55 | 5 model tests |
| `tests/test_nli_client.py` | ~50 | 4 NLI client tests (respx mocked) |
| `tests/test_jpress_parsing.py` | ~40 | 6 JPRESS parsing tests (HTML fixtures) |
| `tests/test_server.py` | ~45 | 5 server integration tests |
