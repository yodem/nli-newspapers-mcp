from __future__ import annotations
from pydantic import BaseModel


DC = "http://purl.org/dc/elements/1.1/"


def _dc_val(raw: dict, field: str) -> str:
    entries = raw.get(f"{DC}{field}", [])
    if not entries:
        return ""
    val = entries[0].get("@value", "")
    return val if isinstance(val, str) else str(val)


class NewspaperRecord(BaseModel):
    title: str
    language: str
    record_id: str
    subjects: str
    publisher: str
    nli_url: str = ""

    @classmethod
    def from_nli_response(cls, raw: dict) -> NewspaperRecord:
        return cls(
            title=_dc_val(raw, "title"),
            language=_dc_val(raw, "language"),
            record_id=_dc_val(raw, "recordid"),
            subjects=_dc_val(raw, "subject"),
            publisher=_dc_val(raw, "publisher"),
            nli_url=raw.get("@id", ""),
        )


class NewspaperMetadata(BaseModel):
    title: str
    alternative_titles: list[str] = []
    publisher: str = ""
    creation_date: str = ""
    language: str = ""
    subjects: str = ""
    doc_id: str = ""

    @classmethod
    def from_iiif_manifest(cls, manifest: dict) -> NewspaperMetadata:
        meta = {m["label"]: m["value"] for m in manifest.get("metadata", [])}
        alt_titles = meta.get("Alternative Title", [])
        if isinstance(alt_titles, str):
            alt_titles = [alt_titles]
        return cls(
            title=manifest.get("label", ""),
            alternative_titles=alt_titles,
            publisher=meta.get("Publisher", ""),
            creation_date=meta.get("Creation Date", ""),
            language=meta.get("Language", ""),
            subjects=meta.get("Subject", ""),
            doc_id=meta.get("Doc Id", ""),
        )


class ArticleResult(BaseModel):
    headline: str
    newspaper_name: str = ""
    pub_code: str = ""
    date: str = ""
    page_number: int = 0
    article_url: str = ""
    snippet: str = ""


class NewspaperTitle(BaseModel):
    name: str
    pub_code: str = ""
    language: str = ""
    region: str = ""
    country: str = ""
    date_from: str = ""
    date_to: str = ""


class IssueInfo(BaseModel):
    date: str
    issue_url: str = ""


class PageText(BaseModel):
    text: str
    newspaper_name: str = ""
    date: str = ""
    page_number: int = 0
