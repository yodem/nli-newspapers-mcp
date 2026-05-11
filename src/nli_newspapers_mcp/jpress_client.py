from __future__ import annotations
import re
from bs4 import BeautifulSoup
from nli_newspapers_mcp.models import ArticleResult, NewspaperTitle, IssueInfo, PageText

# Unicode bidi markers to strip
BIDI_CHARS = re.compile(r'[⁦⁧⁨⁩‏‎‪‫‬]')


def _clean_text(text: str) -> str:
    return BIDI_CHARS.sub('', text).strip()


def _fix_html(html: str) -> str:
    """Fix escaped quotes from Playwright serialization."""
    return html.replace('\\"', '"')


class JpressParser:
    @staticmethod
    def parse_titles(html: str) -> list[NewspaperTitle]:
        soup = BeautifulSoup(_fix_html(html), "lxml")
        titles: list[NewspaperTitle] = []
        for row in soup.select("div.nli-title-browser-row"):
            divs = row.find_all("div", recursive=False)
            if len(divs) < 6:
                continue
            link = divs[0].find("a")
            pub_code = ""
            if link and link.get("href"):
                m = re.search(r"/newspapers/([^?/]+)", link["href"])
                if m:
                    pub_code = m.group(1)
            # Extract text, stripping labels like "שפה", "אזור", "מדינה", "זמין מתאריך", "עד תאריך"
            name = _clean_text(divs[0].get_text())
            lang = _clean_text(divs[1].get_text())
            # Strip the Hebrew label prefix
            lang = re.sub(r'^שפה\s*', '', lang)
            region = re.sub(r'^אזור\s*', '', _clean_text(divs[2].get_text()))
            country = re.sub(r'^מדינה\s*', '', _clean_text(divs[3].get_text()))
            date_from = re.sub(r'^זמין מתאריך\s*', '', _clean_text(divs[4].get_text()))
            date_to = re.sub(r'^עד תאריך\s*', '', _clean_text(divs[5].get_text()))

            titles.append(NewspaperTitle(
                name=name,
                pub_code=pub_code,
                language=lang,
                region=region,
                country=country,
                date_from=date_from,
                date_to=date_to,
            ))
        return titles

    @staticmethod
    def parse_search_results(html: str) -> list[ArticleResult]:
        soup = BeautifulSoup(_fix_html(html), "lxml")
        results: list[ArticleResult] = []
        for entry in soup.select("div.vlistentrymaincell"):
            link = entry.find("a", href=re.compile(r"/article/"))
            if not link:
                continue
            # Clean headline: strip highlight tags and [כתבה] suffix
            headline = link.get_text(strip=True)
            headline = re.sub(r'\[⁨.*?⁩\]', '', headline).strip()
            headline = _clean_text(headline)

            # Get newspaper name + date from second div
            info_divs = entry.find_all("div", recursive=False)
            newspaper_name = ""
            if len(info_divs) >= 2:
                newspaper_name = _clean_text(info_divs[1].get_text())

            href = link.get("href", "")
            pub_match = re.search(r"/newspapers/([^/]+)/", href)
            pub_code = pub_match.group(1) if pub_match else ""

            results.append(ArticleResult(
                headline=headline,
                newspaper_name=newspaper_name,
                pub_code=pub_code,
                article_url=href.split("?")[0],
            ))
        return results

    @staticmethod
    def parse_article_text(html: str) -> PageText:
        soup = BeautifulSoup(_fix_html(html), "lxml")
        container = soup.find(id="documentdisplayleftpanesectiontextcontainer")
        text = ""
        if container:
            for header in container.select(".documentdisplayleftpanesectiontextheader"):
                header.decompose()
            text = container.get_text(separator="\n", strip=True)

        title_el = soup.find("title")
        newspaper_name = _clean_text(title_el.get_text()) if title_el else ""

        return PageText(text=text, newspaper_name=newspaper_name)

    @staticmethod
    def parse_issues(html: str) -> list[IssueInfo]:
        soup = BeautifulSoup(_fix_html(html), "lxml")
        issues: list[IssueInfo] = []
        seen = set()
        for link in soup.find_all("a", href=re.compile(r"/newspapers/[^/]+/\d{4}/\d{2}")):
            href = link["href"]
            date_match = re.search(r"/(\d{4})/(\d{2})", href)
            if not date_match:
                continue
            date_key = f"{date_match.group(1)}-{date_match.group(2)}"
            if date_key in seen:
                continue
            seen.add(date_key)
            issues.append(IssueInfo(
                date=date_key,
                issue_url=href.split("?")[0],
            ))
        return issues
