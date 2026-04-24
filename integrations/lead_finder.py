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
EMAIL_RE = re.compile(r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b')
SKIP_WORDS = {"noreply", "no-reply", "example", "test@", "@sentry", "@privacy",
              "wix.com", "wordpress", "squarespace", "schema", "w3.org"}


@dataclass
class Lead:
    name: str
    location: str
    sector: str
    phone: str = ""
    email: str = ""
    has_website: bool = False   # True ise zaten sitesi var — daha az öncelikli
    website: str = ""           # Mevcut web sitesi URL'i (SEO analizi için)
    maps_url: str = ""


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
                        "fields": "name,website,formatted_phone_number,url",
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

                lead = Lead(
                    name=name, location=location, sector=sector,
                    phone=phone, has_website=bool(website),
                    website=website, maps_url=maps_url,
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


async def _find_email_no_website(session: aiohttp.ClientSession, name: str, location: str) -> str:
    """Web sitesi olmayan işletme için Facebook veya arama sonuçlarından email bul."""
    # Google arama: işletme adı + şehir + email/iletişim
    query = f'"{name}" {location} email OR "e-posta" OR "@gmail" OR "@hotmail" OR "iletisim"'
    search_url = "https://www.google.com/search?q=" + urllib.parse.quote(query)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        async with session.get(
            search_url, headers=headers,
            timeout=aiohttp.ClientTimeout(total=10),
            allow_redirects=True,
        ) as resp:
            text = await resp.text(errors="ignore")
            for match in EMAIL_RE.findall(text):
                if not any(skip in match.lower() for skip in SKIP_WORDS):
                    return match.lower()
    except Exception as e:
        logger.debug(f"Arama email hata [{name}]: {e}")

    return ""


async def _scrape_email(session: aiohttp.ClientSession, url: str) -> str:
    """Web sitesi olan işletmenin contact sayfasından email çek."""
    contact_paths = ["", "/contact", "/iletisim", "/about", "/hakkimizda", "/kontakt", "/impressum"]
    for path in contact_paths:
        try:
            target = url.rstrip("/") + path
            async with session.get(
                target,
                timeout=aiohttp.ClientTimeout(total=8),
                allow_redirects=True,
            ) as resp:
                content_type = resp.headers.get("Content-Type", "")
                if "html" not in content_type:
                    continue
                text = await resp.text(errors="ignore")
                for match in EMAIL_RE.findall(text):
                    if not any(skip in match.lower() for skip in SKIP_WORDS):
                        return match.lower()
        except Exception:
            pass
    return ""
