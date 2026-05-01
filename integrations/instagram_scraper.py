"""
Instagram business lead scraper.
Finds businesses with no website link in their bio — web design prospects.
Uses camoufox for stealth browsing. Requires INSTAGRAM_USER + INSTAGRAM_PASSWORD in .env
"""
import asyncio
import json
import re
from dataclasses import dataclass
from pathlib import Path
from loguru import logger

CACHE_FILE = Path("memory/instagram_leads_cache.json")
CACHE_TTL_DAYS = 14

_EMAIL_RE = re.compile(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,6}')
_PHONE_RE = re.compile(r'[\+]?[\d\s\-\(\)]{9,16}')

# Sektör → Instagram hashtag eşlemeleri
_SECTOR_TAGS: dict[str, list[str]] = {
    "restoran":      ["restaurant", "yemek", "lezzetliyemekler"],
    "restaurant":    ["restaurant", "foodie", "food"],
    "kafe":          ["cafe", "kahve", "coffee"],
    "cafe":          ["cafe", "coffee", "coffeeshop"],
    "berber":        ["barber", "barbershop", "erkekguzellik"],
    "barbershop":    ["barbershop", "barber", "haircut"],
    "otel":          ["hotel", "otel", "butikhotel"],
    "hotel":         ["hotel", "boutique", "travel"],
    "guzellik":      ["beauty", "guzelliksalonu", "makyaj"],
    "beauty salon":  ["beautysalon", "beauty", "nails"],
    "emlak":         ["realestate", "emlak", "satilik"],
    "real estate":   ["realestate", "property", "homes"],
    "dis":           ["dentist", "dishekimi", "agizdishshealth"],
    "dental":        ["dentist", "dental", "smile"],
    "hukuk":         ["law", "lawyer", "avukat"],
    "law":           ["lawfirm", "lawyer", "attorney"],
    "spor":          ["gym", "fitness", "sporsalonu"],
    "gym":           ["gym", "fitness", "workout"],
    "muhasebe":      ["muhasebe", "accounting", "finans"],
}


@dataclass
class InstagramLead:
    username: str
    full_name: str
    bio: str
    email: str
    phone: str
    website: str
    has_website: bool
    followers: int
    sector: str
    location: str

    def to_dict(self) -> dict:
        return self.__dict__


def _cache_key(sector: str, location: str) -> str:
    return f"{sector.lower()}|{location.lower()}"


def _load_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _get_cached(sector: str, location: str) -> list[InstagramLead] | None:
    from datetime import datetime
    cache = _load_cache()
    entry = cache.get(_cache_key(sector, location))
    if not entry:
        return None
    try:
        from datetime import datetime as dt
        cached_at = dt.fromisoformat(entry["cached_at"])
        if (dt.now() - cached_at).days >= CACHE_TTL_DAYS:
            return None
        return [InstagramLead(**l) for l in entry["leads"]]
    except Exception:
        return None


def _set_cache(sector: str, location: str, leads: list[InstagramLead]):
    from datetime import datetime
    cache = _load_cache()
    cache[_cache_key(sector, location)] = {
        "cached_at": datetime.now().isoformat(),
        "leads": [l.to_dict() for l in leads],
    }
    CACHE_FILE.parent.mkdir(exist_ok=True)
    tmp = CACHE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    import os
    os.replace(tmp, CACHE_FILE)


def _extract_email(bio: str) -> str:
    m = _EMAIL_RE.search(bio)
    return m.group(0).lower() if m else ""


def _extract_phone(bio: str) -> str:
    # Remove emails first to avoid false matches
    clean = _EMAIL_RE.sub("", bio)
    m = _PHONE_RE.search(clean)
    if m:
        digits = re.sub(r'\D', '', m.group(0))
        if 9 <= len(digits) <= 15:
            return m.group(0).strip()
    return ""


def _get_hashtags(sector: str, location: str) -> list[str]:
    """Build hashtag list from sector + location."""
    loc_clean = location.lower().replace(" ", "")
    tags = []
    for key, vals in _SECTOR_TAGS.items():
        if key in sector.lower():
            tags = vals[:2]
            break
    if not tags:
        tags = [sector.lower().replace(" ", "")]
    # Add location tag
    return [f"{t}{loc_clean}" for t in tags] + tags[:1]


async def _login(page, username: str, password: str) -> bool:
    """Log in to Instagram."""
    try:
        await page.goto("https://www.instagram.com/accounts/login/", timeout=30000)
        await asyncio.sleep(3)
        await page.fill('input[name="username"]', username)
        await page.fill('input[name="password"]', password)
        await page.click('button[type="submit"]')
        await asyncio.sleep(5)
        # Check if logged in (look for home icon or profile)
        url = page.url
        if "login" not in url:
            logger.info("Instagram login successful")
            return True
        logger.warning("Instagram login failed — check credentials")
        return False
    except Exception as e:
        logger.error(f"Instagram login error: {e}")
        return False


async def _scrape_hashtag(page, tag: str, max_profiles: int = 10) -> list[dict]:
    """Visit a hashtag page and collect profile links."""
    profiles = []
    try:
        await page.goto(f"https://www.instagram.com/explore/tags/{tag}/", timeout=20000)
        await asyncio.sleep(3)
        # Collect post links
        links = await page.query_selector_all('a[href*="/p/"]')
        post_urls = list({await l.get_attribute("href") for l in links[:20]})
        logger.info(f"Instagram #{tag}: {len(post_urls)} post bulundu")

        seen_users = set()
        for post_url in post_urls[:max_profiles * 2]:
            if len(profiles) >= max_profiles:
                break
            try:
                await page.goto(f"https://www.instagram.com{post_url}", timeout=15000)
                await asyncio.sleep(2)

                # Get username from post
                user_el = await page.query_selector('a.x1i10hfl[href*="/"]')
                if not user_el:
                    continue
                user_href = await user_el.get_attribute("href")
                username = user_href.strip("/").split("/")[0]
                if not username or username in seen_users or username == "explore":
                    continue
                seen_users.add(username)

                # Visit profile
                await page.goto(f"https://www.instagram.com/{username}/", timeout=15000)
                await asyncio.sleep(2)

                bio_el = await page.query_selector('div.-vDIg span')
                bio = await bio_el.inner_text() if bio_el else ""

                name_el = await page.query_selector('h1, h2')
                full_name = await name_el.inner_text() if name_el else username

                # Website
                web_el = await page.query_selector('a.x1i10hfl[href*="//"]')
                website = await web_el.get_attribute("href") if web_el else ""

                profiles.append({
                    "username": username,
                    "full_name": full_name.strip(),
                    "bio": bio.strip(),
                    "website": website,
                })
                await asyncio.sleep(1.5)
            except Exception as e:
                logger.debug(f"Instagram post scrape error: {e}")
                continue

    except Exception as e:
        logger.warning(f"Instagram hashtag scrape error #{tag}: {e}")

    return profiles


async def scrape_instagram_leads(
    sector: str,
    location: str,
    max_leads: int = 15,
) -> list[InstagramLead]:
    """Main entry point — returns leads found on Instagram for the given sector/location."""
    cached = _get_cached(sector, location)
    if cached is not None:
        logger.info(f"Instagram cache hit: {len(cached)} lead — {sector}/{location}")
        return cached

    from config import settings
    username = getattr(settings, "instagram_user", "")
    password = getattr(settings, "instagram_password", "")

    if not username or not password:
        logger.warning("Instagram credentials not configured (INSTAGRAM_USER / INSTAGRAM_PASSWORD)")
        return []

    leads: list[InstagramLead] = []
    hashtags = _get_hashtags(sector, location)
    logger.info(f"Instagram scraping: {sector}/{location}, tags={hashtags}")

    try:
        from camoufox.async_api import AsyncCamoufox
        async with AsyncCamoufox(headless=True, humanize=True) as browser:
            page = await browser.new_page()
            logged_in = await _login(page, username, password)
            if not logged_in:
                return []

            seen = set()
            for tag in hashtags[:2]:
                if len(leads) >= max_leads:
                    break
                profiles = await _scrape_hashtag(page, tag, max_profiles=max_leads)
                for p in profiles:
                    uname = p["username"]
                    if uname in seen:
                        continue
                    seen.add(uname)

                    email = _extract_email(p["bio"])
                    phone = _extract_phone(p["bio"])
                    has_website = bool(p.get("website"))

                    # Only include if we have some contact info
                    if not email and not phone and not has_website:
                        continue

                    leads.append(InstagramLead(
                        username=uname,
                        full_name=p["full_name"],
                        bio=p["bio"][:200],
                        email=email,
                        phone=phone,
                        website=p.get("website", ""),
                        has_website=has_website,
                        followers=0,
                        sector=sector,
                        location=location,
                    ))

    except ImportError:
        logger.error("camoufox not installed — run: pip install camoufox")
    except Exception as e:
        logger.error(f"Instagram scrape failed: {e}")

    if leads:
        _set_cache(sector, location, leads)
        logger.info(f"Instagram: {len(leads)} lead bulundu — {sector}/{location}")

    return leads
