from nli_newspapers_mcp.models import (
    NewspaperRecord,
    NewspaperMetadata,
    ArticleResult,
    NewspaperTitle,
    IssueInfo,
    PageText,
)


def test_newspaper_record_from_nli_response():
    raw = {
        "@id": "https://www.nli.org.il/en/journals/NNL-Journals990018346170205171",
        "http://purl.org/dc/elements/1.1/title": [{"@value": "הארץ של ערבית."}],
        "http://purl.org/dc/elements/1.1/language": [{"@value": "heb"}],
        "http://purl.org/dc/elements/1.1/recordid": [{"@value": "990018346170205171"}],
        "http://purl.org/dc/elements/1.1/type": [{"@value": "journal"}],
        "http://purl.org/dc/elements/1.1/subject": [{"@value": "Hebrew newspapers -- Israel"}],
        "http://purl.org/dc/elements/1.1/publisher": [{"@value": "תל אביב"}],
    }
    record = NewspaperRecord.from_nli_response(raw)
    assert record.title == "הארץ של ערבית."
    assert record.language == "heb"
    assert record.record_id == "990018346170205171"
    assert "Hebrew newspapers" in record.subjects


def test_newspaper_metadata_from_iiif():
    manifest = {
        "label": "הארץ של ערבית.",
        "metadata": [
            {"label": "Title", "value": "הארץ של ערבית."},
            {"label": "Publisher", "value": "תל אביב"},
            {"label": "Language", "value": "heb"},
            {"label": "Subject", "value": "Hebrew newspapers -- Israel"},
            {"label": "Doc Id", "value": "NNL-Journals71290283690005171"},
            {"label": "Creation Date", "value": "1929"},
            {"label": "Alternative Title", "value": ["הארץ heb", "Ha'aretz lat"]},
        ],
        "sequences": [],
    }
    meta = NewspaperMetadata.from_iiif_manifest(manifest)
    assert meta.title == "הארץ של ערבית."
    assert meta.language == "heb"
    assert "Ha'aretz lat" in meta.alternative_titles
    assert meta.doc_id == "NNL-Journals71290283690005171"


def test_article_result():
    result = ArticleResult(
        headline="We congratulate the Evening Telegram",
        newspaper_name="The American Hebrew",
        pub_code="americanhebrew",
        date="1880-07-02",
        page_number=1,
        article_url="/he/newspapers/americanhebrew/1880/07/02/01/article/3",
    )
    assert result.headline == "We congratulate the Evening Telegram"
    assert result.pub_code == "americanhebrew"


def test_newspaper_title():
    title = NewspaperTitle(
        name="The American Hebrew",
        pub_code="americanhebrew",
        language="אנגלית",
        region="צפון אמריקה",
        country="ארצות הברית",
        date_from="1880-07-02",
        date_to="1891-04-10",
    )
    assert title.pub_code == "americanhebrew"


def test_page_text():
    page = PageText(
        text="We congratulate the Evening Telegram on its Bar Mitzvah.",
        newspaper_name="The American Hebrew",
        date="1880-07-02",
        page_number=1,
    )
    assert "Bar Mitzvah" in page.text
