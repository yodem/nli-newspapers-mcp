import json
from pathlib import Path
import pytest
import httpx
import respx
from nli_newspapers_mcp.server import call_tool, list_tools
import nli_newspapers_mcp.server as srv

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def reset_server_clients(monkeypatch):
    """Reset global clients before each test."""
    monkeypatch.setenv("NLI_API_KEY", "test-key")
    srv.nli = None
    srv.jpress = None


@pytest.mark.asyncio
async def test_list_tools_returns_all_six():
    tools = await list_tools()
    names = [t.name for t in tools]
    assert len(names) == 6
    assert "search_newspapers" in names
    assert "get_newspaper_metadata" in names
    assert "search_articles" in names
    assert "list_newspaper_titles" in names
    assert "get_newspaper_issues" in names
    assert "get_page_text" in names


@respx.mock
@pytest.mark.asyncio
async def test_call_search_newspapers():
    fixture = json.loads((FIXTURES / "nli_search_response.json").read_text())
    respx.get("https://api.nli.org.il/openlibrary/search").mock(
        return_value=httpx.Response(200, json=fixture)
    )
    result = await call_tool("search_newspapers", {"query": "Hebrew newspapers"})
    assert len(result) == 1
    data = json.loads(result[0].text)
    assert len(data) == 2
    assert data[0]["title"] == "הארץ של ערבית."


@respx.mock
@pytest.mark.asyncio
async def test_call_get_newspaper_metadata():
    fixture = json.loads((FIXTURES / "nli_iiif_manifest.json").read_text())
    respx.get("https://iiif.nli.org.il/IIIFv21/990018346170205171/manifest").mock(
        return_value=httpx.Response(200, json=fixture)
    )
    result = await call_tool("get_newspaper_metadata", {"record_id": "990018346170205171"})
    assert len(result) == 1
    data = json.loads(result[0].text)
    assert data["title"] == "הארץ של ערבית."
    assert "Ha'aretz lat" in data["alternative_titles"]


@pytest.mark.asyncio
async def test_call_unknown_tool():
    result = await call_tool("nonexistent_tool", {})
    assert "Unknown tool" in result[0].text


@pytest.mark.asyncio
async def test_call_search_newspapers_missing_api_key(monkeypatch):
    monkeypatch.delenv("NLI_API_KEY", raising=False)
    srv.nli = None
    result = await call_tool("search_newspapers", {"query": "test"})
    assert "NLI_API_KEY" in result[0].text
