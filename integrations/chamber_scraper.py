"""
Sanayi odası ve iş dizini scraper — Maps API'ye ek lead kaynağı.

Türkiye : firmarehberi.com.tr, enfes.com.tr
Almanya : gelbeseiten.de
İngiltere: yell.com
ABD      : yellowpages.com
"""
import asyncio
import json
import os
import re
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import aiohttp
from loguru import logger

CHAMBER_CACHE_FILE = Path("memory/chamber_leads_cache.json")
CHAMBER_CACHE_TTL_DAYS = 30

_HEADERS_TR = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
}
_HEADERS_EN = {**_HEADERS_TR, "Accept-Language": "en-US,en;q=0.9"}
_HEADERS_DE = {**_HEADERS_TR, "Accept-Language": "de-DE,de;q=0.9,en;q=0.8"}

EMAIL_RE   = re.compile(r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,6}\b')
PHONE_RE   = re.compile(r'(?:\+?\d[\d\s\-\(\)]{7,14}\d)')
WEBSITE_RE = re.compile(r'https?://[^\s"\'<>]{4,80}', re.IGNORECASE)

_SKIP_EMAIL = {"noreply", "no-reply", "example", "test@", "@sentry", "wix.com",
               "wordpress", "squarespace", "schema", "w3.org", "placeholder",
               "domain.com", "email.com", "sifre", "password"}

_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".bmp"}


# ── Cache ────────────────────────────────────────────────────────────────────

def _cache_key(sector: str, location: str) -> str:
    return f"chamber|{sector.lower().strip()}|{location.lower().strip()}"


def _get_cached(sector: str, location: str):
    if not CHAMBER_CACHE_FILE.exists():
        return None
    try:
        data = json.loads(CHAMBER_CACHE_FILE.read_text(encoding="utf-8"))
        entry = data.get(_cache_key(sector, location))
        if not entry:
            return None
        if (datetime.now() - datetime.fromisoformat(entry["cached_at"])).days >= CHAMBER_CACHE_TTL_DAYS:
            return None
        from integrations.lead_finder import Lead
        return [Lead(**l) for l in entry["leads"]]
    except Exception:
        return None


def _set_cached(sector: str, location: str, leads: list):
    CHAMBER_CACHE_FILE.parent.mkdir(exist_ok=True)
    try:
        data = json.loads(CHAMBER_CACHE_FILE.read_text(encoding="utf-8")) if CHAMBER_CACHE_FILE.exists() else {}
    except Exception:
        data = {}
    data[_cache_key(sector, location)] = {
        "cached_at": datetime.now().isoformat(),
        "leads": [
            {"name": l.name, "location": l.location, "sector": l.sector,
             "phone": l.phone, "email": l.email, "has_website": l.has_website,
             "website": l.website, "maps_url": l.maps_url,
             "rating": l.rating, "review_count": l.review_count}
            for l in leads
        ],
    }
    tmp = CHAMBER_CACHE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, CHAMBER_CACHE_FILE)


# ── Yardımcı ─────────────────────────────────────────────────────────────────

def _valid_email(email: str) -> bool:
    e = email.lower()
    if any(s in e for s in _SKIP_EMAIL):
        return False
    tld = "." + e.rsplit(".", 1)[-1]
    if tld in _IMAGE_EXTS:
        return False
    domain = e.split("@", 1)[-1]
    return len(domain) >= 4 and not domain[0].isdigit()


def _extract_emails(html: str) -> list[str]:
    found = []
    for m in re.findall(r'mailto:([A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,6})', html, re.I):
        if _valid_email(m):
            found.append(m.lower())
    if not found:
        for m in EMAIL_RE.findall(html):
            if _valid_email(m):
                found.append(m.lower())
    return found


def _clean_text(s: str) -> str:
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', s)).strip()


# ── Türkiye: firmarehberi.com.tr ─────────────────────────────────────────────

_TR_CITY_MAP = {
    "istanbul": "istanbul", "ankara": "ankara", "izmir": "izmir",
    "bursa": "bursa", "antalya": "antalya", "adana": "adana",
    "konya": "konya", "gaziantep": "gaziantep", "mersin": "mersin",
    "kayseri": "kayseri", "samsun": "samsun", "trabzon": "trabzon",
    "erzurum": "erzurum", "diyarbakir": "diyarbakir", "tekirdag": "tekirdag",
    "kocaeli": "kocaeli", "sakarya": "sakarya", "denizli": "denizli",
    "hatay": "hatay", "manisa": "manisa", "ordu": "ordu", "rize": "rize",
    "edirne": "edirne", "canakkale": "canakkale", "malatya": "malatya",
    "sanliurfa": "sanliurfa", "eskisehir": "eskisehir", "kahramanmaras": "kahramanmaras",
    "kutahya": "kutahya", "bilecik": "bilecik", "corum": "corum",
    "artvin": "artvin", "mugla": "mugla", "duzce": "duzce", "kars": "kars",
    "sivas": "sivas", "bodrum": "bodrum", "alanya": "alanya",
}

_TR_SECTOR_MAP = {
    "restoran": "restoran", "kafe": "kafe", "pastane": "pastane",
    "dis hekimi": "dis-hekimi", "eczane": "eczane", "veteriner": "veteriner",
    "spor salonu": "spor-salonu", "avukat": "avukat", "muhasebe": "muhasebe",
    "guzellik salonu": "guzellik-salonu", "berber": "berber",
    "emlakci": "emlak", "insaat": "insaat", "nakliyat": "nakliyat",
    "oto servis": "oto-servis", "matbaa": "matbaa",
    "mobilya uretimi": "mobilya", "gunes enerjisi": "gunes-enerjisi",
    "reklam ajansi": "reklam", "danismanlik": "danismanlik",
    "guvenlik sirketi": "guvenlik", "yazilim gelistirme": "yazilim",
    "teknik servis": "teknik-servis", "kargo hizmetleri": "kargo",
    "metal isleme": "metal", "makine uretimi": "makine",
}


async def _scrape_firmarehberi(session: aiohttp.ClientSession, sector: str, location: str) -> list:
    from integrations.lead_finder import Lead

    city = _TR_CITY_MAP.get(location.lower(), location.lower().replace(" ", "-"))
    sector_slug = _TR_SECTOR_MAP.get(sector.lower(), urllib.parse.quote(sector.lower().replace(" ", "-")))

    leads = []
    urls_to_try = [
        f"https://www.firmarehberi.com.tr/{city}/{sector_slug}/",
        f"https://www.firmarehberi.com.tr/arama/?q={urllib.parse.quote(sector)}&sehir={urllib.parse.quote(location)}",
    ]

    for url in urls_to_try:
        try:
            async with session.get(url, headers=_HEADERS_TR, timeout=aiohttp.ClientTimeout(total=15),
                                   allow_redirects=True) as resp:
                if resp.status != 200:
                    continue
                html = await resp.text(errors="ignore")

            # Firma adları — ortak pattern'ler
            names = re.findall(r'(?:class="(?:firma-adi|company-name|isim|title)[^"]*"[^>]*>|<h[23][^>]*>)\s*([^<]{3,80})', html, re.IGNORECASE)
            phones = re.findall(r'(?:tel:|phone:|telefon:?)\s*([+\d\s\-\(\)]{8,18})', html, re.IGNORECASE)
            websites_found = re.findall(r'href="(https?://(?!(?:www\.firmarehberi|google|facebook|instagram|twitter)\.)[\w.\-/]{5,60})"', html)

            if not names:
                # Genel başlık yakala
                names = re.findall(r'<a[^>]+href="[^"]*firma[^"]*"[^>]*>\s*([^<]{3,60})\s*</a>', html, re.IGNORECASE)

            seen = set()
            for i, name in enumerate(names[:15]):
                name = _clean_text(name)
                if len(name) < 3 or name.lower() in seen:
                    continue
                seen.add(name.lower())
                phone = phones[i].strip() if i < len(phones) else ""
                website = websites_found[i] if i < len(websites_found) else ""
                leads.append(Lead(
                    name=name, location=location, sector=sector,
                    phone=phone, has_website=bool(website),
                    website=website, maps_url="",
                ))

            if leads:
                logger.info(f"firmarehberi: {len(leads)} firma — {sector}/{location}")
                break
        except Exception as e:
            logger.debug(f"firmarehberi hata [{sector}/{location}]: {e}")

    return leads


# ── Almanya: gelbeseiten.de ───────────────────────────────────────────────────

_DE_CITY_MAP = {
    "berlin": "Berlin", "hamburg": "Hamburg", "munich": "Muenchen",
    "cologne": "Koeln", "frankfurt": "Frankfurt-am-Main",
    "stuttgart": "Stuttgart", "nuremberg": "Nuernberg",
    "dresden": "Dresden", "leipzig": "Leipzig", "bremen": "Bremen",
    "hannover": "Hannover", "dortmund": "Dortmund",
    "dusseldorf": "Duesseldorf", "vienna": "Wien", "zurich": "Zuerich",
    "bern": "Bern", "graz": "Graz",
}


async def _scrape_gelbeseiten(session: aiohttp.ClientSession, sector: str, location: str) -> list:
    from integrations.lead_finder import Lead

    city = _DE_CITY_MAP.get(location.lower(), location)
    url = f"https://www.gelbeseiten.de/suche/{urllib.parse.quote(sector)}/{urllib.parse.quote(city)}"

    leads = []
    try:
        async with session.get(url, headers=_HEADERS_DE, timeout=aiohttp.ClientTimeout(total=15),
                               allow_redirects=True) as resp:
            if resp.status != 200:
                return []
            html = await resp.text(errors="ignore")

        # Gelbe Seiten HTML pattern'leri
        names = re.findall(r'(?:class="[^"]*(?:mod-CompanyName|company-name|Treffer-Name)[^"]*"[^>]*>)\s*([^<]{3,80})', html, re.IGNORECASE)
        if not names:
            names = re.findall(r'<h\d[^>]*class="[^"]*name[^"]*"[^>]*>\s*([^<]{3,60})\s*</h\d>', html, re.IGNORECASE)

        phones = re.findall(r'(?:tel:|Telefon:?)\s*([+\d\s\-\/\(\)]{8,20})', html, re.IGNORECASE)
        websites_found = re.findall(r'href="(https?://(?!(?:www\.gelbeseiten|google|facebook)\.)[\w.\-/]{5,60})"', html)

        seen = set()
        for i, name in enumerate(names[:12]):
            name = _clean_text(name)
            if len(name) < 3 or name.lower() in seen:
                continue
            seen.add(name.lower())
            phone = phones[i].strip() if i < len(phones) else ""
            website = websites_found[i] if i < len(websites_found) else ""
            leads.append(Lead(
                name=name, location=location, sector=sector,
                phone=phone, has_website=bool(website), website=website, maps_url="",
            ))

        if leads:
            logger.info(f"gelbeseiten: {len(leads)} firma — {sector}/{location}")
    except Exception as e:
        logger.debug(f"gelbeseiten hata [{sector}/{location}]: {e}")

    return leads


# ── İngiltere: yell.com ──────────────────────────────────────────────────────

async def _scrape_yell(session: aiohttp.ClientSession, sector: str, location: str) -> list:
    from integrations.lead_finder import Lead

    url = (f"https://www.yell.com/ucs/UcsSearchAction.do"
           f"?keywords={urllib.parse.quote(sector)}&location={urllib.parse.quote(location)}")
    leads = []
    try:
        async with session.get(url, headers=_HEADERS_EN, timeout=aiohttp.ClientTimeout(total=15),
                               allow_redirects=True) as resp:
            if resp.status != 200:
                return []
            html = await resp.text(errors="ignore")

        names = re.findall(r'(?:class="[^"]*(?:businessName|listing-title|business-name)[^"]*"[^>]*>)\s*([^<]{3,60})', html, re.IGNORECASE)
        phones = re.findall(r'(?:tel:|phone:)\s*([+\d\s\-\(\)]{8,18})', html, re.IGNORECASE)
        websites_found = re.findall(r'href="(https?://(?!(?:www\.yell|google|facebook)\.)[\w.\-/]{5,60})"', html)

        seen = set()
        for i, name in enumerate(names[:12]):
            name = _clean_text(name)
            if len(name) < 3 or name.lower() in seen:
                continue
            seen.add(name.lower())
            phone = phones[i].strip() if i < len(phones) else ""
            website = websites_found[i] if i < len(websites_found) else ""
            leads.append(Lead(
                name=name, location=location, sector=sector,
                phone=phone, has_website=bool(website), website=website, maps_url="",
            ))

        if leads:
            logger.info(f"yell.com: {len(leads)} firma — {sector}/{location}")
    except Exception as e:
        logger.debug(f"yell hata [{sector}/{location}]: {e}")

    return leads


# ── ABD: yellowpages.com ─────────────────────────────────────────────────────

async def _scrape_yellowpages(session: aiohttp.ClientSession, sector: str, location: str) -> list:
    from integrations.lead_finder import Lead

    url = (f"https://www.yellowpages.com/search"
           f"?search_terms={urllib.parse.quote(sector)}&geo_location_terms={urllib.parse.quote(location)}")
    leads = []
    try:
        async with session.get(url, headers=_HEADERS_EN, timeout=aiohttp.ClientTimeout(total=15),
                               allow_redirects=True) as resp:
            if resp.status != 200:
                return []
            html = await resp.text(errors="ignore")

        names = re.findall(r'(?:class="[^"]*(?:business-name|listing-name)[^"]*"[^>]*>)\s*<[^>]+>\s*([^<]{3,60})', html, re.IGNORECASE)
        if not names:
            names = re.findall(r'<a[^>]+class="[^"]*business-name[^"]*"[^>]*>\s*([^<]{3,60})\s*</a>', html, re.IGNORECASE)
        phones = re.findall(r'(?:class="[^"]*phone[^"]*"[^>]*>)\s*([+\d\s\-\(\)\.]{8,18})', html, re.IGNORECASE)
        websites_found = re.findall(r'href="(https?://(?!(?:www\.yellowpages|google|facebook)\.)[\w.\-/]{5,60})"', html)

        seen = set()
        for i, name in enumerate(names[:12]):
            name = _clean_text(name)
            if len(name) < 3 or name.lower() in seen:
                continue
            seen.add(name.lower())
            phone = phones[i].strip() if i < len(phones) else ""
            website = websites_found[i] if i < len(websites_found) else ""
            leads.append(Lead(
                name=name, location=location, sector=sector,
                phone=phone, has_website=bool(website), website=website, maps_url="",
            ))

        if leads:
            logger.info(f"yellowpages: {len(leads)} firma — {sector}/{location}")
    except Exception as e:
        logger.debug(f"yellowpages hata [{sector}/{location}]: {e}")

    return leads


# ── Email zenginleştirme ─────────────────────────────────────────────────────

async def _enrich_emails(session: aiohttp.ClientSession, leads: list) -> list:
    """Websitesi olan leadlerden email çek; olmayanlar için Google arama dene."""
    from integrations.lead_finder import _scrape_email, _find_email_no_website
    enriched = []
    for lead in leads:
        if lead.email:
            enriched.append(lead)
            continue
        if lead.website:
            lead.email = await _scrape_email(session, lead.website)
        if not lead.email:
            lead.email = await _find_email_no_website(session, lead.name, lead.location)
        enriched.append(lead)
        await asyncio.sleep(0.5)
    return enriched


# ── Ana fonksiyon ─────────────────────────────────────────────────────────────

# Hangi şehirler hangi scraper'a gidiyor
_GERMAN_CITIES  = {"berlin", "hamburg", "munich", "cologne", "frankfurt", "stuttgart",
                   "nuremberg", "dresden", "leipzig", "bremen", "hannover", "dortmund",
                   "dusseldorf", "vienna", "zurich", "bern", "graz"}
_UK_CITIES      = {"london", "manchester", "birmingham", "leeds", "glasgow", "liverpool",
                   "sheffield", "bristol", "newcastle", "nottingham", "edinburgh", "cardiff"}
_US_CA_AU_CITIES = {"new york", "los angeles", "chicago", "houston", "miami", "phoenix",
                    "dallas", "atlanta", "toronto", "vancouver", "montreal", "sydney",
                    "melbourne", "brisbane", "dubai", "abu dhabi"}


async def scrape_directory(sector: str, location: str) -> list:
    """Sektör ve şehire göre uygun dizini scrape et, Lead listesi döndür."""
    cached = _get_cached(sector, location)
    if cached is not None:
        logger.info(f"Chamber cache hit: {len(cached)} lead — {sector}/{location}")
        return cached

    loc_lower = location.lower()
    leads = []

    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        if loc_lower in _GERMAN_CITIES:
            leads = await _scrape_gelbeseiten(session, sector, location)
        elif loc_lower in _UK_CITIES:
            leads = await _scrape_yell(session, sector, location)
        elif loc_lower in _US_CA_AU_CITIES:
            leads = await _scrape_yellowpages(session, sector, location)
        else:
            # Varsayılan: Türkiye
            leads = await _scrape_firmarehberi(session, sector, location)

        # Sadece emaili olmayan leadleri zenginleştir (limit: 8 firma)
        leads_to_enrich = [l for l in leads if not l.email][:8]
        if leads_to_enrich:
            enriched = await _enrich_emails(session, leads_to_enrich)
            # Güncellenmiş leadleri geri koy
            email_map = {l.name: l.email for l in enriched}
            for l in leads:
                if not l.email and l.name in email_map:
                    l.email = email_map[l.name]

    leads_with_email = [l for l in leads if l.email]
    logger.info(f"Chamber toplam: {len(leads)} firma, {len(leads_with_email)} email — {sector}/{location}")

    if leads:
        _set_cached(sector, location, leads)

    return leads
