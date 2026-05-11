from __future__ import annotations
from urllib.parse import urlencode
import httpx
from nli_newspapers_mcp.models import NewspaperRecord, NewspaperMetadata


class NLIClient:
    SEARCH_URL = "https://api.nli.org.il/openlibrary/search"
    IIIF_URL = "https://iiif.nli.org.il/IIIFv21"

    def __init__(self, api_key: str):
        self._api_key = api_key
        self._http = httpx.AsyncClient(timeout=30)

    async def search_newspapers(
        self,
        query: str,
        language: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        max_results: int = 10,
    ) -> list[NewspaperRecord]:
        query_parts = [f"subject,contains,{query},AND"]
        if language:
            query_parts.append(f"language,exact,{language},AND")
        if start_date:
            query_parts.append(f"start_date,contains,{start_date},AND")
        if end_date:
            query_parts.append(f"end_date,contains,{end_date},AND")

        query_str = ";".join(query_parts)
        if query_str.endswith(",AND"):
            query_str = query_str[:-4]

        # Build the query string manually so commas are not percent-encoded,
        # matching the NLI API's expected format and allowing string-based URL assertions.
        safe_params = urlencode(
            {
                "api_key": self._api_key,
                "material_type": "periodical",
                "items_per_page": str(min(max_results, 50)),
                "output_format": "json",
            }
        )
        url = f"{self.SEARCH_URL}?{safe_params}&query={query_str}"

        resp = await self._http.get(url)
        resp.raise_for_status()

        text = resp.text.strip()
        if text.startswith("Query string is not Valid"):
            raise ValueError(text)

        data = resp.json()
        if not isinstance(data, list):
            raise ValueError(f"Unexpected response: {text[:200]}")

        return [NewspaperRecord.from_nli_response(item) for item in data]

    async def get_newspaper_metadata(self, record_id: str) -> NewspaperMetadata:
        url = f"{self.IIIF_URL}/{record_id}/manifest"
        resp = await self._http.get(url)
        resp.raise_for_status()
        manifest = resp.json()
        return NewspaperMetadata.from_iiif_manifest(manifest)

    async def close(self):
        await self._http.aclose()
