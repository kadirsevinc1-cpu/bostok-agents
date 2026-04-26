"""
Potansiyel müşteri (lead) bulucu.
Hedef: Web sitesi OLMAYAN işletmeler — bunlar web tasarım hizmetine ihtiyaç duyar.
Email bulma: Facebook sayfası veya Google arama sonuçları üzerinden.
"""
import asyncio
import re
import urllib.parse
import aiohttp
from dataclasses import dataclass
from loguru import logger

MAPS_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
MAPS_DETAIL_URL = "https://maps.googleapis.com/maps/api/place/details/json"
EMAIL_RE = re.compile(r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,6}\b')
_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".bmp"}
SKIP_WORDS = {"noreply", "no-reply", "example", "test@", "@sentry", "@privacy",
              "wix.com", "wordpress", "squarespace", "schema", "w3.org",
              "@2x", "@3x", "placeholder", "domain.com", "email.com"}


def _valid_email(email: str) -> bool:
    """Sahte email eşleşmelerini filtrele."""
    if any(skip in email.lower() for skip in SKIP_WORDS):
        return False
    # Resim uzantısı TLD gibi görünüyorsa reddet (.png, .jpg, vb.)
    tld = "." + email.rsplit(".", 1)[-1].lower()
    if tld in _IMAGE_EXTS:
        return False
    # @ sonrası kısım çok kısa veya sayı içeriyorsa şüpheli
    domain = email.split("@", 1)[-1]
    if len(domain) < 4 or domain[0].isdigit():
        return False
    return True


@dataclass
class Lead:
    name: str
    location: str
    sector: str
    phone: str = ""
    email: str = ""
    has_website: bool = False
    website: str = ""
    maps_url: str = ""
    rating: float = 0.0          # Google Maps puanı (1-5)
    review_count: int = 0        # Değerlendirme sayısı


async def find_leads(sector: str, location: str, api_key: str = "") -> list[Lead]:
    if not api_key:
        return []
    return await _maps_leads(sector, location, api_key)


async def _maps_leads(sector: str, location: str, api_key: str) -> list[Lead]:
    no_site_leads = []
    has_site_leads = []

    params = {"query": f"{sector} {location}", "key": api_key}
    try:
        async with aiohttp.ClientSession() as session:
            # 1. Text search — place_id listesi al
            async with session.get(
                MAPS_SEARCH_URL, params=params,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                data = await resp.json()

            status = data.get("status")
            if status not in ("OK", "ZERO_RESULTS"):
                logger.warning(f"Maps API durumu: {status}")
                return []

            places = data.get("results", [])[:15]

            # 2. Her yer için Place Details — website + telefon al
            for place in places:
                place_id = place.get("place_id", "")
                name = place.get("name", "")
                website = ""
                phone = ""
                maps_url = f"https://maps.google.com/?place_id={place_id}"

                if place_id:
                    detail_params = {
                        "place_id": place_id,
                        "fields": "name,website,formatted_phone_number,url,rating,user_ratings_total",
                        "key": api_key,
                    }
                    async with session.get(
                        MAPS_DETAIL_URL, params=detail_params,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as dr:
                        detail = await dr.json()
                    result = detail.get("result", {})
                    website = result.get("website", "")
                    phone = result.get("formatted_phone_number", "")
                    maps_url = result.get("url", maps_url)
                    rating = float(result.get("rating", 0) or 0)
                    review_count = int(result.get("user_ratings_total", 0) or 0)
                else:
                    rating = float(place.get("rating", 0) or 0)
                    review_count = int(place.get("user_ratings_total", 0) or 0)

                lead = Lead(
                    name=name, location=location, sector=sector,
                    phone=phone, has_website=bool(website),
                    website=website, maps_url=maps_url,
                    rating=rating, review_count=review_count,
                )

                if not website:
                    # Web sitesi yok → asıl hedef kitle
                    # Email bulmaya çalış: Facebook veya Google arama
                    lead.email = await _find_email_no_website(session, name, location)
                    no_site_leads.append(lead)
                else:
                    # Web sitesi var ama eski/kötü olabilir → ikincil hedef
                    lead.email = await _scrape_email(session, website)
                    if lead.email:
                        has_site_leads.append(lead)

                await asyncio.sleep(0.3)

    except Exception as e:
        logger.error(f"Maps hata [{sector}/{location}]: {e}")

    # Önce web sitesi olmayanlar
    leads = no_site_leads + has_site_leads
    no_site_with_email = sum(1 for l in no_site_leads if l.email)
    logger.info(
        f"Lead: {len(no_site_leads)} sitesiz ({no_site_with_email} email), "
        f"{len(has_site_leads)} siteli-email ({sector}/{location})"
    )
    return leads


MAILTO_RE = re.compile(r'mailto:([A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,6})', re.IGNORECASE)
COMMON_PREFIXES = ["info", "iletisim", "contact", "hello", "merhaba", "destek", "support", "bilgi"]


def _extract_emails(html: str) -> list[str]:
    """mailto: linklerini önce dene (daha güvenilir), sonra regex."""
    found = []
    for m in MAILTO_RE.findall(html):
        if _valid_email(m):
            found.append(m.lower())
    if not found:
        for m in EMAIL_RE.findall(html):
            if _valid_email(m):
                found.append(m.lower())
    return found


def _guess_domain_emails(website: str) -> list[str]:
    """Web sitesi domain'inden yaygın prefix'lerle email tahmin et."""
    try:
        from urllib.parse import urlparse
        domain = urlparse(website).netloc.lstrip("www.")
        if not domain or len(domain) < 4:
            return []
        return [f"{p}@{domain}" for p in COMMON_PREFIXES]
    except Exception:
        return []


async def _search_email(session: aiohttp.ClientSession, name: str, location: str) -> str:
    """SerpApi → Serper.dev → Google scrape sırasıyla email ara."""
    try:
        from config import settings
        serpapi_key = getattr(settings, "serpapi_api_key", "")
        serper_key  = getattr(settings, "serper_api_key", "")
    except Exception:
        serpapi_key = serper_key = ""

    query = f'"{name}" {location} email OR "@gmail" OR "@hotmail" OR "iletisim"'

    # 1. SerpApi
    if serpapi_key:
        try:
            async with session.get(
                "https://serpapi.com/search",
                params={"q": query, "api_key": serpapi_key, "num": 10, "hl": "tr"},
                timeout=aiohttp.ClientTimeout(total=12),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    text = " ".join(
                        r.get("snippet", "") + " " + r.get("title", "")
                        for r in data.get("organic_results", [])
                    )
                    for m in _extract_emails(text):
                        logger.debug(f"SerpApi email: {m} [{name}]")
                        return m
        except Exception as e:
            logger.debug(f"SerpApi hata [{name}]: {e}")

    # 2. Serper.dev
    if serper_key:
        try:
            async with session.post(
                "https://google.serper.dev/search",
                json={"q": query, "num": 10, "hl": "tr"},
                headers={"X-API-KEY": serper_key, "Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=12),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    text = " ".join(
                        r.get("snippet", "") + " " + r.get("title", "")
                        for r in data.get("organic", [])
                    )
                    for m in _extract_emails(text):
                        logger.debug(f"Serper email: {m} [{name}]")
                        return m
        except Exception as e:
            logger.debug(f"Serper hata [{name}]: {e}")

    # 3. Direkt Google scrape
    search_url = "https://www.google.com/search?q=" + urllib.parse.quote(query)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}
    try:
        async with session.get(
            search_url, headers=headers,
            timeout=aiohttp.ClientTimeout(total=10),
            allow_redirects=True,
        ) as resp:
            text = await resp.text(errors="ignore")
            for m in _extract_emails(text):
                return m
    except Exception as e:
        logger.debug(f"Google scrape hata [{name}]: {e}")

    return ""


async def _find_email_no_website(session: aiohttp.ClientSession, name: str, location: str) -> str:
    return await _search_email(session, name, location)


async def _scrape_email(session: aiohttp.ClientSession, url: str) -> str:
    """Web sitesi olan işletmenin sayfalarından email çek; bulamazsa domain tahmini."""
    contact_paths = ["", "/contact", "/iletisim", "/about", "/hakkimizda",
                     "/kontakt", "/impressum", "/bize-ulasin", "/en/contact"]
    for path in contact_paths:
        try:
            target = url.rstrip("/") + path
            async with session.get(
                target,
                timeout=aiohttp.ClientTimeout(total=8),
                allow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0"},
            ) as resp:
                if "html" not in resp.headers.get("Content-Type", ""):
                    continue
                text = await resp.text(errors="ignore")
                emails = _extract_emails(text)
                if emails:
                    return emails[0]
        except Exception:
            pass

    # Bulunamadı → domain'den tahmin et
    guesses = _guess_domain_emails(url)
    if guesses:
        logger.debug(f"Domain tahmini kullanıldı: {guesses[0]} [{url}]")
        return guesses[0]

    return ""
