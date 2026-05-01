"""
LinkedIn lead finder — safe approach.
Uses Google to find LinkedIn profiles (no LinkedIn automation, no ban risk).
Generates personalized connection messages via LLM.
Results are sent to Telegram for manual outreach by the user.
"""
import asyncio
import json
import re
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from loguru import logger

import aiohttp

CACHE_FILE = Path("memory/linkedin_leads_cache.json")
CACHE_TTL_DAYS = 7

_PROFILE_URL_RE = re.compile(r'linkedin\.com/in/([\w\-]+)', re.IGNORECASE)


@dataclass
class LinkedInLead:
    profile_url: str
    name: str
    title: str
    company: str
    sector: str
    location: str
    snippet: str

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


def _get_cached(sector: str, location: str) -> list[LinkedInLead] | None:
    from datetime import datetime as dt
    cache = _load_cache()
    entry = cache.get(_cache_key(sector, location))
    if not entry:
        return None
    try:
        cached_at = dt.fromisoformat(entry["cached_at"])
        if (dt.now() - cached_at).days >= CACHE_TTL_DAYS:
            return None
        return [LinkedInLead(**l) for l in entry["leads"]]
    except Exception:
        return None


def _set_cache(sector: str, location: str, leads: list[LinkedInLead]):
    from datetime import datetime as dt
    cache = _load_cache()
    cache[_cache_key(sector, location)] = {
        "cached_at": dt.now().isoformat(),
        "leads": [l.to_dict() for l in leads],
    }
    CACHE_FILE.parent.mkdir(exist_ok=True)
    tmp = CACHE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    import os
    os.replace(tmp, CACHE_FILE)


# Title keywords that indicate decision makers
_OWNER_TITLES = {
    "owner", "founder", "co-founder", "ceo", "director", "manager",
    "proprietor", "partner", "president", "sahibi", "kurucu", "yönetici",
    "geschäftsführer", "inhaber", "gérant", "directeur", "eigenaar",
}


def _is_decision_maker(title: str) -> bool:
    t = title.lower()
    return any(kw in t for kw in _OWNER_TITLES)


async def _google_search_linkedin(
    session: aiohttp.ClientSession,
    sector: str,
    location: str,
    max_results: int = 8,
) -> list[LinkedInLead]:
    """Find LinkedIn profiles via Google search."""
    # Search specifically for decision makers in this sector/location
    query = f'site:linkedin.com/in "{sector}" "{location}" (owner OR founder OR director OR manager)'
    url = "https://www.google.com/search?q=" + urllib.parse.quote(query) + f"&num={max_results}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }

    leads = []
    try:
        async with session.get(url, headers=headers,
                               timeout=aiohttp.ClientTimeout(total=12),
                               allow_redirects=True) as resp:
            if resp.status != 200:
                return []
            text = await resp.text(errors="ignore")

        # Extract linkedin.com/in/ URLs and snippets from result
        # Google result structure: <h3>Name — Title at Company</h3> + snippet
        # Use regex to find profile slugs
        matches = _PROFILE_URL_RE.findall(text)
        seen = set()

        # Find surrounding context for each match
        for slug in matches:
            if slug in seen or slug.lower() in ("in", "jobs", "company", "learning"):
                continue
            seen.add(slug)

            profile_url = f"https://www.linkedin.com/in/{slug}"

            # Try to extract name + title from surrounding text
            idx = text.find(slug)
            context = text[max(0, idx - 200): idx + 300]
            # Strip HTML tags
            context_clean = re.sub(r'<[^>]+>', ' ', context)
            context_clean = re.sub(r'\s+', ' ', context_clean).strip()

            # Heuristic: first line-like segment is often "Name - Title at Company"
            lines = [l.strip() for l in context_clean.split('·') if l.strip()]
            name = lines[0][:60] if lines else slug
            title = lines[1][:80] if len(lines) > 1 else ""
            snippet = context_clean[:200]

            # Extract company name from title
            company = ""
            if " at " in title.lower():
                company = title.lower().split(" at ")[-1].strip().title()
            elif " - " in title:
                parts = title.split(" - ")
                if len(parts) > 1:
                    company = parts[-1].strip()

            leads.append(LinkedInLead(
                profile_url=profile_url,
                name=name,
                title=title,
                company=company,
                sector=sector,
                location=location,
                snippet=snippet,
            ))

            if len(leads) >= max_results:
                break

    except Exception as e:
        logger.warning(f"LinkedIn Google search error [{sector}/{location}]: {e}")

    return leads


async def generate_linkedin_message(lead: LinkedInLead, lang: str = "en") -> str:
    """Generate a personalized LinkedIn connection message via LLM."""
    from core.llm_router import router

    lang_names = {"tr": "Turkish", "en": "English", "de": "German",
                  "nl": "Dutch", "fr": "French"}
    lang_name = lang_names.get(lang, "English")

    prompt = (
        f"Write a short LinkedIn connection request message in {lang_name} "
        f"for {lead.name} ({lead.title} at {lead.company or lead.sector}, {lead.location}).\n\n"
        f"Context: We are Bostok.dev, a web design agency. "
        f"We want to connect because we help {lead.sector} businesses get professional websites.\n\n"
        f"Rules:\n"
        f"- Max 300 characters (LinkedIn connection note limit)\n"
        f"- Personalize using their role ({lead.title}) and sector ({lead.sector})\n"
        f"- Do NOT mention we found them on LinkedIn\n"
        f"- Natural, human tone — not salesy\n"
        f"- No links, no website URL\n"
        f"Output ONLY the message text."
    )

    try:
        result = await router.chat([{"role": "user", "content": prompt}], max_tokens=150)
        return result.strip()[:300]
    except Exception as e:
        logger.error(f"LinkedIn message generation error: {e}")
        return ""


async def find_and_notify(
    sector: str,
    location: str,
    lang: str = "en",
    max_leads: int = 5,
) -> list[dict]:
    """
    Find LinkedIn leads and generate messages.
    Returns list of dicts with profile_url + message for Telegram notification.
    """
    cached = _get_cached(sector, location)
    if cached is not None:
        logger.info(f"LinkedIn cache hit: {len(cached)} — {sector}/{location}")
        leads = cached
    else:
        async with aiohttp.ClientSession() as session:
            leads = await _google_search_linkedin(session, sector, location, max_results=max_leads * 2)
        if leads:
            _set_cache(sector, location, leads)
        logger.info(f"LinkedIn: {len(leads)} profil bulundu — {sector}/{location}")

    results = []
    for lead in leads[:max_leads]:
        msg = await generate_linkedin_message(lead, lang=lang)
        if msg:
            results.append({
                "profile_url": lead.profile_url,
                "name": lead.name,
                "title": lead.title,
                "company": lead.company,
                "message": msg,
            })
        await asyncio.sleep(0.5)

    return results
