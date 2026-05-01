"""
Potansiyel müşteri (lead) bulucu.
Hedef: Web sitesi OLMAYAN işletmeler — bunlar web tasarım hizmetine ihtiyaç duyar.
Email bulma: Facebook sayfası veya Google arama sonuçları üzerinden.
"""
import asyncio
import json
import os
import re
import socket
import urllib.parse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import aiohttp
from loguru import logger

LEADS_CACHE_FILE = Path("memory/leads_cache.json")
LEADS_CACHE_TTL_DAYS = 30


def _cache_key(sector: str, location: str) -> str:
    return f"{sector.lower().strip()}|{location.lower().strip()}"


def _load_leads_cache() -> dict:
    if LEADS_CACHE_FILE.exists():
        try:
            return json.loads(LEADS_CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_leads_cache(data: dict):
    LEADS_CACHE_FILE.parent.mkdir(exist_ok=True)
    tmp = LEADS_CACHE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, LEADS_CACHE_FILE)


def _get_cached_leads(sector: str, location: str):
    cache = _load_leads_cache()
    entry = cache.get(_cache_key(sector, location))
    if not entry:
        return None
    try:
        cached_at = datetime.fromisoformat(entry["cached_at"])
        if (datetime.now() - cached_at).days >= LEADS_CACHE_TTL_DAYS:
            return None
    except Exception:
        return None
    try:
        return [Lead(**lead) for lead in entry["leads"]]
    except Exception:
        return None


def _set_cached_leads(sector: str, location: str, leads):
    cache = _load_leads_cache()
    cache[_cache_key(sector, location)] = {
        "cached_at": datetime.now().isoformat(),
        "leads": [
            {
                "name": l.name, "location": l.location, "sector": l.sector,
                "phone": l.phone, "email": l.email, "has_website": l.has_website,
                "website": l.website, "maps_url": l.maps_url,
                "rating": l.rating, "review_count": l.review_count,
            }
            for l in leads
        ],
    }
    _save_leads_cache(cache)


async def _domain_exists(domain: str) -> bool:
    """Domain A kaydı var mı kontrol et (tamamen sahte domain'leri filtreler)."""
    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, socket.gethostbyname, domain)
        return True
    except socket.gaierror:
        return False


def _check_mx(domain: str) -> bool:
    """MX kaydı kontrolü — thread'de çalışır."""
    try:
        import dns.resolver
        dns.resolver.resolve(domain, "MX")
        return True
    except Exception:
        return False


async def _has_mx(domain: str) -> bool:
    """Domain'de MX kaydı var mı? Yoksa email sunucusu yok demektir."""
    try:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _check_mx, domain)
    except Exception:
        return False

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
    cached = _get_cached_leads(sector, location)
    if cached is not None:
        logger.info(f"Leads cache hit: {len(cached)} lead — {sector}/{location}")
        return cached

    from core.location_expander import expand_location
    sub_locations = expand_location(location)

    leads: list[Lead] = []
    seen_names: set[str] = set()

    if api_key:
        for sub_loc in sub_locations:
            sub_leads = await _maps_leads(sector, sub_loc, api_key)
            for lead in sub_leads:
                key = lead.name.lower().strip()
                if key not in seen_names:
                    seen_names.add(key)
                    leads.append(lead)
        if len(sub_locations) > 1:
            logger.info(f"Ilce aramasi: {len(sub_locations)} bolge -> {len(leads)} benzersiz lead ({sector}/{location})")

    try:
        from integrations.chamber_scraper import scrape_directory
        chamber_leads = await scrape_directory(sector, location)
        for cl in chamber_leads:
            key = cl.name.lower().strip()
            if key not in seen_names:
                seen_names.add(key)
                leads.append(cl)
        if chamber_leads:
            logger.info(f"Dizin scraper {len(chamber_leads)} firma ekledi — toplam: {len(leads)}")
    except Exception as e:
        logger.debug(f"Chamber scraper atlandi: {e}")

    if leads:
        _set_cached_leads(sector, location, leads)
    return leads


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

            places = list(data.get("results", []))

            # Pagination — 2. sayfa (Maps API 2 sn bekleme zorunlu)
            next_token = data.get("next_page_token")
            if next_token and len(places) >= 20:
                await asyncio.sleep(2)
                async with session.get(
                    MAPS_SEARCH_URL,
                    params={"pagetoken": next_token, "key": api_key},
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp2:
                    data2 = await resp2.json()
                places.extend(data2.get("results", []))
            places = places[:40]

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


async def _scrape_facebook_email(session: aiohttp.ClientSession, name: str, location: str) -> str:
    """Facebook business page'den email veya telefon çek."""
    query = urllib.parse.quote(f"{name} {location} site:facebook.com")
    search_url = f"https://www.google.com/search?q={query}&num=3"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}
    try:
        async with session.get(search_url, headers=headers,
                               timeout=aiohttp.ClientTimeout(total=8),
                               allow_redirects=True) as resp:
            if resp.status != 200:
                return ""
            text = await resp.text(errors="ignore")
            # Google snippet'larında email var mı?
            for m in _extract_emails(text):
                logger.debug(f"Facebook Google snippet email: {m} [{name}]")
                return m
    except Exception as e:
        logger.debug(f"Facebook scrape hata [{name}]: {e}")
    return ""


def _whois_email(domain: str) -> str:
    """WHOIS kaydından alan adı sahibinin emailini çek — ücretsiz, API gerektirmez."""
    try:
        import whois as _whois
        w = _whois.whois(domain)
        emails = w.emails
        if not emails:
            return ""
        if isinstance(emails, str):
            emails = [emails]
        # Privacy-proxy emaillerini filtrele
        skip = ("privacy", "proxy", "protect", "whoisguard", "contact.gandi",
                "registrar", "abuse", "noreply", "no-reply", "domainsbyproxy",
                "markmonitor", "godaddy", "networksolutions", "namecheap",
                "whoisrequest", "hostmaster", "webmaster")
        for e in emails:
            e = e.strip().lower()
            if e and "@" in e and not any(s in e for s in skip):
                return e
    except Exception:
        pass
    return ""


async def _hunter_domain_search(session: aiohttp.ClientSession, domain: str) -> str:
    """Hunter.io domain search — alan adı için email bul (25 ücretsiz/ay)."""
    try:
        from config import settings as _cfg
        if not _cfg.hunter_api_key or not domain:
            return ""
        url = "https://api.hunter.io/v2/domain-search"
        params = {"domain": domain, "api_key": _cfg.hunter_api_key, "limit": 5}
        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=8)) as resp:
            if resp.status != 200:
                return ""
            data = await resp.json()
            emails = data.get("data", {}).get("emails", [])
            if emails:
                # Önce owner/manager/director rollerini tercih et
                priority = ["owner", "founder", "ceo", "director", "manager", "contact", "info"]
                for role in priority:
                    for e in emails:
                        if role in (e.get("type", "") + " " + e.get("value", "")).lower():
                            return e["value"]
                return emails[0]["value"]
    except Exception as e:
        logger.debug(f"Hunter.io error [{domain}]: {e}")
    return ""


async def _find_email_no_website(session: aiohttp.ClientSession, name: str, location: str) -> str:
    # 1. Web/SerpApi/Serper arama
    email = await _search_email(session, name, location)
    if email:
        return email
    # 2. Facebook sayfası snippet'ından dene
    email = await _scrape_facebook_email(session, name, location)
    if email:
        return email
    # 3. İşletme adından tahmin edilen domain'i WHOIS'te ara
    try:
        import re as _re
        slug = _re.sub(r"[^a-z0-9]", "", name.lower())[:20]
        loc_slug = _re.sub(r"[^a-z]", "", location.lower())[:8]
        for candidate in [f"{slug}.com", f"{slug}.de", f"{slug}.nl",
                          f"{slug}{loc_slug}.com", f"{slug}.co.uk"]:
            w_email = _whois_email(candidate)
            if w_email:
                logger.debug(f"WHOIS (tahmini domain) email buldu: {w_email} [{candidate}]")
                return w_email
    except Exception:
        pass
    return ""


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

    # Bulunamadı → WHOIS email dene (ücretsiz, API yok)
    try:
        from urllib.parse import urlparse as _up
        domain = _up(url).netloc.lstrip("www.")
        if domain:
            whois_email = _whois_email(domain)
            if whois_email:
                logger.debug(f"WHOIS email buldu: {whois_email} [{domain}]")
                return whois_email
    except Exception:
        pass

    # Hunter.io domain search (API key varsa)
    try:
        from urllib.parse import urlparse as _up
        domain = _up(url).netloc.lstrip("www.")
        if domain:
            hunter_email = await _hunter_domain_search(session, domain)
            if hunter_email:
                logger.debug(f"Hunter.io email buldu: {hunter_email} [{domain}]")
                return hunter_email
    except Exception:
        pass

    # Son çare → domain'den tahmin et (MX kaydı varsa)
    guesses = _guess_domain_emails(url)
    if guesses:
        try:
            from urllib.parse import urlparse as _up
            domain = _up(url).netloc.lstrip("www.")
            if domain and await _has_mx(domain):
                logger.debug(f"Domain MX onaylı, tahmin kullanıldı: {guesses[0]} [{url}]")
                return guesses[0]
            else:
                logger.debug(f"Domain MX kaydı yok, tahmin atlandı: {domain}")
        except Exception:
            pass

    return ""
