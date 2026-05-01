"""
Yelp Fusion API lead finder.
Free tier: 5000 API calls/day. Returns businesses with name, website, phone, rating.
Get API key: https://www.yelp.com/developers → Create App (free, no credit card).
"""
import asyncio
from dataclasses import dataclass

import aiohttp
from loguru import logger

YELP_SEARCH_URL = "https://api.yelp.com/v3/businesses/search"

# Sector name → Yelp category alias
_SECTOR_MAP: dict[str, str] = {
    # Food & Drink
    "restoran":          "restaurants",
    "restaurant":        "restaurants",
    "restaurants":       "restaurants",
    "kafe":              "cafes",
    "cafe":              "cafes",
    "cafes":             "cafes",
    "pastane":           "bakeries",
    "bakery":            "bakeries",
    "bar":               "bars",
    "fast food":         "burgers",
    "catering":          "catering",
    # Beauty & Wellness
    "berber":            "barbers",
    "barbershop":        "barbers",
    "barbers":           "barbers",
    "guzellik salonu":   "beautysvc",
    "beauty salon":      "beautysvc",
    "spa":               "spas",
    "gym":               "gyms",
    "spor salonu":       "fitness",
    "fitness":           "fitness",
    "nail":              "nails",
    "tirnak":            "nails",
    # Medical
    "dis hekimi":        "dentists",
    "dentist":           "dentists",
    "klinik":            "mediccenters",
    "clinic":            "mediccenters",
    "eczane":            "pharmacies",
    "pharmacy":          "pharmacies",
    "veteriner":         "veterinarians",
    "veterinary":        "veterinarians",
    # Professional
    "avukat":            "lawyers",
    "lawyer":            "lawyers",
    "muhasebe":          "accountants",
    "accounting":        "accountants",
    "sigorta":           "insurance",
    "insurance":         "insurance",
    "emlak":             "realestateagents",
    "real estate":       "realestateagents",
    # Accommodation
    "otel":              "hotels",
    "hotel":             "hotels",
    "pansiyon":          "bedbreakfast",
    # Retail
    "mobilya":           "furniture",
    "furniture":         "furniture",
    "elektronik":        "electronics",
    "electronics":       "electronics",
    "giyim":             "fashion",
    "clothes":           "fashion",
    # Auto
    "oto servis":        "autorepair",
    "car repair":        "autorepair",
    "oto galeri":        "car_dealers",
    # Other
    "okuloncesi":        "kindergartens",
    "dershane":          "tutoring",
    "fotograf":          "photographers",
    "photography":       "photographers",
}


def _get_category(sector: str) -> str:
    s = sector.lower().strip()
    if s in _SECTOR_MAP:
        return _SECTOR_MAP[s]
    # Partial match — only keys longer than 3 chars to avoid "bar"→"barbers" collisions
    for key, cat in _SECTOR_MAP.items():
        if len(key) > 3 and (key in s or s in key):
            return cat
    return s  # pass raw term to Yelp as fallback


@dataclass
class YelpLead:
    name: str
    location: str
    sector: str
    website: str = ""
    phone: str = ""
    email: str = ""
    rating: float = 0.0
    review_count: int = 0
    yelp_url: str = ""


async def find_yelp_leads(
    sector: str,
    location: str,
    api_key: str,
    limit: int = 50,
) -> list[YelpLead]:
    """
    Search Yelp for businesses. Returns name + phone + rating — no detail
    calls needed (Yelp API doesn't expose business website URLs).
    Email finding happens in lead_finder via domain guess + scraping.
    """
    category = _get_category(sector)
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        async with aiohttp.ClientSession() as session:
            params = {
                "term": sector,
                "location": location,
                "limit": min(limit, 50),
                "categories": category,
            }
            async with session.get(
                YELP_SEARCH_URL,
                headers=headers,
                params=params,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 401:
                    logger.warning("Yelp API: gecersiz API key")
                    return []
                if resp.status == 429:
                    logger.warning("Yelp API: rate limit (5000/gun doldu)")
                    return []
                if resp.status != 200:
                    logger.warning(f"Yelp API HTTP {resp.status} — {sector}/{location}")
                    return []
                data = await resp.json()

        businesses = data.get("businesses", [])
        if not businesses:
            logger.info(f"Yelp: sonuc yok — {sector}/{location} (category={category})")
            return []

        leads = [
            YelpLead(
                name=biz.get("name", ""),
                location=location,
                sector=sector,
                phone=biz.get("display_phone", "") or biz.get("phone", ""),
                rating=float(biz.get("rating", 0) or 0),
                review_count=int(biz.get("review_count", 0) or 0),
                yelp_url=biz.get("url", ""),
            )
            for biz in businesses
            if biz.get("name")
        ]

        logger.info(f"Yelp: {len(leads)} isletme bulundu — {sector}/{location} (category={category})")
        return leads

    except asyncio.TimeoutError:
        logger.warning(f"Yelp timeout — {sector}/{location}")
        return []
    except Exception as e:
        logger.warning(f"Yelp hata — {sector}/{location}: {e}")
        return []
