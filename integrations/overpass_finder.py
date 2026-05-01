"""
Overpass API (OpenStreetMap) lead finder — completely free, no API key.
Returns businesses with name, website, phone from OSM data.
"""
import asyncio
import re
from dataclasses import dataclass

import aiohttp
from loguru import logger

OVERPASS_URL  = "https://overpass-api.de/api/interpreter"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
TIMEOUT = 30
_bbox_cache: dict[str, tuple[float,float,float,float]] = {}

# Sector name → OSM tags to search
_SECTOR_TAGS: dict[str, list[str]] = {
    # Food & Drink
    "restoran":         ["amenity=restaurant"],
    "restaurant":       ["amenity=restaurant"],
    "kafe":             ["amenity=cafe"],
    "cafe":             ["amenity=cafe"],
    "pastane":          ["amenity=cafe", "shop=bakery"],
    "bakery":           ["shop=bakery"],
    "bar":              ["amenity=bar"],
    "fast food":        ["amenity=fast_food"],
    # Beauty & Wellness
    "berber":           ["shop=hairdresser"],
    "barbershop":       ["shop=hairdresser"],
    "guzellik salonu":  ["shop=beauty"],
    "beauty salon":     ["shop=beauty"],
    "spa":              ["leisure=spa"],
    "gym":              ["leisure=fitness_centre"],
    "spor salonu":      ["leisure=fitness_centre"],
    # Medical
    "dis hekimi":       ["amenity=dentist"],
    "dentist":          ["amenity=dentist"],
    "klinik":           ["amenity=clinic"],
    "clinic":           ["amenity=clinic"],
    "eczane":           ["amenity=pharmacy"],
    "pharmacy":         ["amenity=pharmacy"],
    "veteriner":        ["amenity=veterinary"],
    # Professional
    "avukat":           ["office=lawyer"],
    "lawyer":           ["office=lawyer"],
    "muhasebe":         ["office=accountant"],
    "accounting":       ["office=accountant"],
    "sigorta":          ["office=insurance"],
    "insurance":        ["office=insurance"],
    "emlak":            ["office=estate_agent"],
    "real estate":      ["office=estate_agent"],
    # Accommodation
    "otel":             ["tourism=hotel"],
    "hotel":            ["tourism=hotel"],
    "pansiyon":         ["tourism=guest_house"],
    # Retail
    "market":           ["shop=supermarket", "shop=convenience"],
    "eczane":           ["amenity=pharmacy"],
    "mobilya":          ["shop=furniture"],
    "furniture":        ["shop=furniture"],
    "elektronik":       ["shop=electronics"],
    "electronics":      ["shop=electronics"],
    "giyim":            ["shop=clothes"],
    "clothes":          ["shop=clothes"],
    # Auto
    "oto servis":       ["shop=car_repair"],
    "car repair":       ["shop=car_repair"],
    "oto galeri":       ["shop=car"],
    # Other
    "okuloncesi":       ["amenity=kindergarten"],
    "dershane":         ["amenity=school"],
    "turizm":           ["tourism=travel_agency"],
    "tourism":          ["tourism=travel_agency"],
    "fotograf":         ["shop=photo"],
}

_DEFAULT_TAGS = ["amenity=restaurant", "shop=retail", "office=company"]


def _get_tags(sector: str) -> list[str]:
    s = sector.lower().strip()
    # Direct match
    if s in _SECTOR_TAGS:
        return _SECTOR_TAGS[s]
    # Partial match
    for key, tags in _SECTOR_TAGS.items():
        if key in s or s in key:
            return tags
    return _DEFAULT_TAGS


async def _get_bbox(city: str) -> tuple[float, float, float, float] | None:
    """Nominatim → get bounding box for a city name."""
    if city in _bbox_cache:
        return _bbox_cache[city]
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(
                NOMINATIM_URL,
                params={"q": city, "format": "json", "limit": 1},
                headers={"User-Agent": "Bostok.dev/1.0"},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as r:
                data = await r.json()
        if not data:
            return None
        bb = data[0].get("boundingbox", [])
        if len(bb) < 4:
            return None
        s_, n_, w_, e_ = float(bb[0]), float(bb[1]), float(bb[2]), float(bb[3])
        _bbox_cache[city] = (s_, n_, w_, e_)
        return (s_, n_, w_, e_)
    except Exception as e:
        logger.debug(f"Nominatim hata [{city}]: {e}")
        return None


def _build_query(tags: list[str], bbox: tuple, limit: int = 50) -> str:
    """Build Overpass QL query with bounding box."""
    s, n, w, e = bbox
    tag_queries = []
    for tag in tags:
        k, v = tag.split("=", 1)
        tag_queries.append(f'node["{k}"="{v}"]({s},{w},{n},{e});')
        tag_queries.append(f'way["{k}"="{v}"]({s},{w},{n},{e});')

    tag_block = "\n  ".join(tag_queries)
    return f"""[out:json][timeout:{TIMEOUT}];
(
  {tag_block}
);
out body center {limit};
"""


@dataclass
class OsmLead:
    name: str
    website: str = ""
    phone: str = ""
    email: str = ""
    location: str = ""
    sector: str = ""


async def find_osm_leads(sector: str, location: str, limit: int = 40) -> list[OsmLead]:
    """Query Overpass API for businesses in a city. Returns leads with website/phone."""
    tags = _get_tags(sector)

    bbox = await _get_bbox(location)
    if not bbox:
        logger.warning(f"Overpass: bbox bulunamadı — {location}")
        return []

    query = _build_query(tags, bbox, limit=limit)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                OVERPASS_URL,
                data={"data": query},
                timeout=aiohttp.ClientTimeout(total=TIMEOUT + 5),
                headers={"User-Agent": "Bostok.dev lead finder"},
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"Overpass HTTP {resp.status} — {sector}/{location}")
                    return []
                data = await resp.json()
    except asyncio.TimeoutError:
        logger.warning(f"Overpass timeout — {sector}/{location}")
        return []
    except Exception as e:
        logger.warning(f"Overpass hata — {sector}/{location}: {e}")
        return []

    leads: list[OsmLead] = []
    seen: set[str] = set()

    for el in data.get("elements", []):
        tags_el = el.get("tags", {})
        name = tags_el.get("name", "").strip()
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())

        website = tags_el.get("website", "") or tags_el.get("contact:website", "")
        phone   = tags_el.get("phone", "") or tags_el.get("contact:phone", "")
        email   = tags_el.get("email", "") or tags_el.get("contact:email", "")

        # Clean website URL
        if website and not website.startswith("http"):
            website = "https://" + website

        leads.append(OsmLead(
            name=name,
            website=website,
            phone=phone,
            email=email,
            location=location,
            sector=sector,
        ))

    logger.info(f"Overpass: {len(leads)} işletme bulundu — {sector}/{location} (tags: {tags})")
    return leads
