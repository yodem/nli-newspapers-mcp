from pathlib import Path
from nli_newspapers_mcp.jpress_client import JpressParser

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_titles():
    html = (FIXTURES / "jpress_titles_page.html").read_text()
    titles = JpressParser.parse_titles(html)
    assert len(titles) > 100
    # Check first title has required fields
    first = titles[0]
    assert first.name
    assert first.pub_code
    assert first.language


def test_parse_titles_has_pub_code():
    html = (FIXTURES / "jpress_titles_page.html").read_text()
    titles = JpressParser.parse_titles(html)
    # All should have pub_code extracted from links
    with_codes = [t for t in titles if t.pub_code]
    assert len(with_codes) > 100


def test_parse_search_results():
    html = (FIXTURES / "jpress_search_results.html").read_text()
    results = JpressParser.parse_search_results(html)
    assert len(results) == 20
    first = results[0]
    assert "Evening" in first.headline or "Telegram" in first.headline
    assert first.article_url
    assert "americanhebrew" in first.pub_code


def test_parse_search_results_newspaper_info():
    html = (FIXTURES / "jpress_search_results.html").read_text()
    results = JpressParser.parse_search_results(html)
    first = results[0]
    assert "American Hebrew" in first.newspaper_name


def test_parse_article_text():
    html = (FIXTURES / "jpress_article_page.html").read_text()
    page = JpressParser.parse_article_text(html)
    assert len(page.text) > 20
    assert "Telegram" in page.text


def test_parse_issues():
    html = (FIXTURES / "jpress_newspaper_page.html").read_text()
    issues = JpressParser.parse_issues(html)
    assert len(issues) > 10
    assert issues[0].date
    assert issues[0].issue_url
