import json
from pathlib import Path
import pytest
import httpx
import respx
from nli_newspapers_mcp.nli_client import NLIClient

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def nli_client():
    return NLIClient(api_key="test-key")


@pytest.fixture
def search_response():
    return json.loads((FIXTURES / "nli_search_response.json").read_text())


@pytest.fixture
def iiif_manifest():
    return json.loads((FIXTURES / "nli_iiif_manifest.json").read_text())


@respx.mock
@pytest.mark.asyncio
async def test_search_newspapers(nli_client, search_response):
    respx.get("https://api.nli.org.il/openlibrary/search").mock(
        return_value=httpx.Response(200, json=search_response)
    )
    results = await nli_client.search_newspapers(query="Hebrew newspapers")
    assert len(results) == 2
    assert results[0].title == "הארץ של ערבית."
    assert results[0].record_id == "990018346170205171"


@respx.mock
@pytest.mark.asyncio
async def test_search_newspapers_with_language_filter(nli_client, search_response):
    route = respx.get("https://api.nli.org.il/openlibrary/search").mock(
        return_value=httpx.Response(200, json=search_response)
    )
    await nli_client.search_newspapers(query="newspapers", language="heb")
    assert "language,exact,heb" in str(route.calls[0].request.url)


@respx.mock
@pytest.mark.asyncio
async def test_get_newspaper_metadata(nli_client, iiif_manifest):
    respx.get("https://iiif.nli.org.il/IIIFv21/990018346170205171/manifest").mock(
        return_value=httpx.Response(200, json=iiif_manifest)
    )
    meta = await nli_client.get_newspaper_metadata("990018346170205171")
    assert meta.title == "הארץ של ערבית."
    assert "Ha'aretz lat" in meta.alternative_titles
    assert meta.language == "heb"


@respx.mock
@pytest.mark.asyncio
async def test_search_newspapers_api_error(nli_client):
    respx.get("https://api.nli.org.il/openlibrary/search").mock(
        return_value=httpx.Response(200, text="Query string is not Valid.")
    )
    with pytest.raises(ValueError, match="not Valid"):
        await nli_client.search_newspapers(query="ab")
