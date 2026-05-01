"""
Site Hunter — competitor website analysis for Website Idea Hunter.
Searches DuckDuckGo, fetches HTML concurrently, extracts competitive signals.
"""
import asyncio
import re
from loguru import logger
import aiohttp

_TIMEOUT  = aiohttp.ClientTimeout(total=8, connect=4)
_HEADERS  = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
_HEX_RE  = re.compile(r'#([0-9a-fA-F]{6})\b')
_SKIP_HEX = {
    "ffffff", "000000", "fffffe", "fafafa", "f5f5f5", "f0f0f0",
    "e0e0e0", "cccccc", "333333", "222222", "111111", "444444",
    "555555", "666666", "888888", "999999", "aaaaaa", "dddddd",
}
_CTA_KW = {
    "quote", "contact", "request", "order", "free", "trial",
    "get started", "learn more", "buy", "shop", "book",
    "anfrage", "angebot", "kontakt", "kaufen", "bestellen", "kostenlos",
    "teklif", "iletişim", "başvur", "ücretsiz",
    "offerte", "aanvragen", "gratis",
    "devis", "demander", "gratuit", "commencer",
}


def _ddg_search(query: str, max_results: int) -> list[str]:
    from ddgs import DDGS
    urls: list[str] = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            url = r.get("href", "")
            if url and url.startswith("http") and url not in urls:
                urls.append(url)
    return urls


def _top_colors(html: str) -> list[str]:
    counts: dict[str, int] = {}
    for m in _HEX_RE.finditer(html):
        c = m.group(1).lower()
        if c not in _SKIP_HEX:
            counts[c] = counts.get(c, 0) + 1
    top = sorted(counts, key=lambda x: -counts[x])[:5]
    return [f"#{c}" for c in top]


def _ctas(soup) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for el in soup.find_all(["button", "a"]):
        raw = el.get_text(strip=True)
        key = raw.lower()
        if not raw or len(raw) > 70 or key in seen:
            continue
        if any(kw in key for kw in _CTA_KW):
            seen.add(key)
            out.append(raw)
            if len(out) >= 8:
                break
    return out


def _nav_items(soup) -> list[str]:
    nav = soup.find("nav")
    if not nav:
        return []
    return [a.get_text(strip=True) for a in nav.find_all("a") if a.get_text(strip=True)][:10]


async def _analyze(url: str, session: aiohttp.ClientSession) -> dict | None:
    try:
        async with session.get(url, headers=_HEADERS, timeout=_TIMEOUT,
                               allow_redirects=True, ssl=False) as resp:
            if resp.status != 200:
                return None
            if "text/html" not in resp.headers.get("content-type", ""):
                return None
            html = await resp.text(errors="replace")
    except Exception as e:
        logger.debug(f"fetch {url}: {e}")
        return None

    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        title = soup.title.get_text(strip=True)[:120] if soup.title else ""
        h1s   = [h.get_text(strip=True) for h in soup.find_all("h1")][:3]
        meta  = ""
        md = soup.find("meta", attrs={"name": "description"})
        if md:
            meta = (md.get("content") or "")[:200]

        return {
            "url":          url,
            "title":        title,
            "h1":           h1s,
            "meta":         meta,
            "nav":          _nav_items(soup),
            "ctas":         _ctas(soup),
            "colors":       _top_colors(html),
            "has_form":     bool(soup.find("form")),
            "has_whatsapp": "wa.me" in html or "whatsapp" in html.lower(),
            "has_chat":     any(s in html for s in ("tawk.to", "intercom", "drift.com", "crisp.chat")),
        }
    except Exception as e:
        logger.debug(f"parse {url}: {e}")
        return None


async def run_hunt(sector: str, country: str, max_sites: int = 10) -> list[dict]:
    """
    Search DuckDuckGo for competitor sites, fetch + analyze them concurrently.
    Returns list of analysis dicts (only successfully fetched sites).
    """
    query = f"{sector} {country} website"
    logger.info(f"SiteHunter: '{query}'")

    loop = asyncio.get_event_loop()
    try:
        urls = await loop.run_in_executor(None, _ddg_search, query, max_sites + 6)
    except Exception as e:
        logger.warning(f"SiteHunter DDG error: {e}")
        return []

    urls = urls[:max_sites]
    if not urls:
        return []

    logger.info(f"SiteHunter: fetching {len(urls)} sites")
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(*[_analyze(u, session) for u in urls])

    out = [r for r in results if r]
    logger.info(f"SiteHunter: {len(out)}/{len(urls)} sites analyzed")
    return out
