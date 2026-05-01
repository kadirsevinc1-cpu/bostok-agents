"""Pexels photo fetcher — returns a landscape photo URL for a given sector category."""
import json
import random
from pathlib import Path
from loguru import logger

import aiohttp

_CACHE_FILE = Path("memory/pexels_photo_cache.json")
_CACHE_TTL_DAYS = 30

_QUERIES: dict[str, str] = {
    "food":        "cozy restaurant interior",
    "health":      "modern medical clinic interior",
    "legal":       "professional law office",
    "beauty":      "modern beauty salon",
    "realestate":  "modern house exterior real estate",
    "auto":        "auto repair garage professional",
    "education":   "modern classroom school",
    "hotel":       "hotel lobby luxury",
    "tech":        "modern office technology workspace",
    "retail":      "modern retail store interior",
    "industrial":  "modern factory warehouse",
}


def _load_cache() -> dict:
    if _CACHE_FILE.exists():
        try:
            return json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_cache(data: dict) -> None:
    _CACHE_FILE.parent.mkdir(exist_ok=True)
    tmp = _CACHE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    import os
    os.replace(tmp, _CACHE_FILE)


def _cached(sector: str) -> str | None:
    from datetime import datetime as dt
    cache = _load_cache()
    entry = cache.get(sector)
    if not entry:
        return None
    try:
        if (dt.now() - dt.fromisoformat(entry["cached_at"])).days < _CACHE_TTL_DAYS:
            urls = entry.get("urls", [])
            return random.choice(urls) if urls else None
    except Exception:
        pass
    return None


async def get_sector_photo(sector: str, api_key: str) -> str:
    """
    Return a Pexels CDN photo URL for the sector.
    Returns "" when no key or fetch fails.
    """
    if not api_key:
        return ""

    cached = _cached(sector)
    if cached:
        return cached

    query = _QUERIES.get(sector, "professional business")
    url   = "https://api.pexels.com/v1/search"
    params = {"query": query, "per_page": 8, "orientation": "landscape"}
    headers = {"Authorization": api_key}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers,
                                   timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status != 200:
                    logger.warning(f"Pexels API error {resp.status} for {sector}")
                    return ""
                data = await resp.json()

        photos = data.get("photos", [])
        if not photos:
            return ""

        # Use medium-sized photo (800px wide) — fast load, good quality
        urls = [
            ph["src"].get("large", ph["src"].get("medium", ""))
            for ph in photos
            if ph.get("src")
        ]
        urls = [u for u in urls if u]

        if not urls:
            return ""

        # Cache for 30 days
        cache = _load_cache()
        cache[sector] = {"cached_at": __import__("datetime").datetime.now().isoformat(), "urls": urls}
        _save_cache(cache)

        logger.info(f"Pexels: {len(urls)} photos cached for sector '{sector}'")
        return random.choice(urls)

    except Exception as e:
        logger.warning(f"Pexels fetch error for {sector}: {e}")
        return ""
