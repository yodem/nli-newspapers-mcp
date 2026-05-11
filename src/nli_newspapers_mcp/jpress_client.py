from __future__ import annotations
import asyncio
import os
import re
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
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


class JpressClient:
    BASE_URL = "https://www.nli.org.il/he/newspapers"

    def __init__(self):
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._pw = None
        self._lock = asyncio.Lock()

    async def _ensure_browser(self):
        if self._page is not None:
            return
        async with self._lock:
            if self._page is not None:
                return
            self._pw = await async_playwright().start()
            headless = os.environ.get("PLAYWRIGHT_HEADLESS", "true").lower() == "true"
            self._browser = await self._pw.chromium.launch(headless=headless)
            self._context = await self._browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            self._page = await self._context.new_page()
            await self._page.goto(f"{self.BASE_URL}/titles", wait_until="domcontentloaded", timeout=60000)
            # Wait for Cloudflare challenge to resolve
            try:
                await self._page.wait_for_function(
                    "() => !document.title.includes('Just a moment')",
                    timeout=30000,
                )
            except Exception:
                pass
            await self._page.wait_for_load_state("domcontentloaded")

    async def _get_page_html(self, url: str) -> str:
        await self._ensure_browser()
        assert self._page is not None
        await self._page.goto(url, wait_until="domcontentloaded", timeout=60000)
        try:
            await self._page.wait_for_function(
                "() => !document.title.includes('Just a moment')",
                timeout=15000,
            )
        except Exception:
            pass
        await asyncio.sleep(1)
        return await self._page.content()

    async def list_titles(self, language: str | None = None, region: str | None = None) -> list[NewspaperTitle]:
        html = await self._get_page_html(f"{self.BASE_URL}/titles")
        titles = JpressParser.parse_titles(html)
        if language:
            titles = [t for t in titles if language in t.language]
        if region:
            titles = [t for t in titles if region in t.region]
        return titles

    async def search_articles(
        self,
        query: str,
        newspaper: str | None = None,
        max_results: int = 20,
    ) -> list[ArticleResult]:
        # Navigate to search page and submit form via JS
        await self._ensure_browser()
        assert self._page is not None
        await self._page.goto(f"{self.BASE_URL}/search", wait_until="networkidle")
        # Fill and submit form
        await self._page.evaluate(f"""
            document.querySelector('#inputtxq').value = {repr(query)};
            document.querySelector('#searchpagesearchform').submit();
        """)
        await self._page.wait_for_load_state("networkidle")
        html = await self._page.content()
        results = JpressParser.parse_search_results(html)
        if newspaper:
            results = [r for r in results if r.pub_code == newspaper]
        return results[:max_results]

    async def get_issues(self, pub_code: str, year: int | None = None) -> list[IssueInfo]:
        url = f"{self.BASE_URL}/{pub_code}"
        html = await self._get_page_html(url)
        issues = JpressParser.parse_issues(html)
        if year:
            issues = [i for i in issues if i.date.startswith(str(year))]
        return issues

    async def get_page_text(self, page_url: str) -> PageText:
        if not page_url.startswith("http"):
            page_url = f"https://www.nli.org.il{page_url}"
        await self._ensure_browser()
        assert self._page is not None
        await self._page.goto(page_url, wait_until="networkidle")
        # Remove tutorial overlay if present
        await self._page.evaluate("document.getElementById('viewertutorial')?.remove()")
        # Wait for text container to potentially load
        try:
            await self._page.wait_for_selector(
                "#documentdisplayleftpanesectiontextcontainer",
                timeout=5000,
            )
        except Exception:
            pass
        html = await self._page.content()
        return JpressParser.parse_article_text(html)

    async def close(self):
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()
        self._page = None
        self._context = None
        self._browser = None
        self._pw = None
