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
YELP_DETAIL_URL = "https://api.yelp.com/v3/businesses/{id}"

# Sector name → Yelp category alias
_SECTOR_MAP: dict[str, str] = {
    # Food & Drink
    "restoran":          "restaurants",
    "restaurant":        "restaurants",
    "kafe":              "cafes",
    "cafe":              "cafes",
    "pastane":           "bakeries",
    "bakery":            "bakeries",
    "bar":               "bars",
    "fast food":         "burgers",
    "catering":          "catering",
    # Beauty & Wellness
    "berber":            "barbers",
    "barbershop":        "barbers",
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
    for key, cat in _SECTOR_MAP.items():
        if key in s or s in key:
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
    fetch_details_count: int = 20,
) -> list[YelpLead]:
    """
    Search Yelp for businesses. Fetches website URL from details endpoint
    for the top `fetch_details_count` results (saves API quota for the rest).
    """
    category = _get_category(sector)
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        async with aiohttp.ClientSession() as session:
            # 1. Search
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
                    logger.warning("Yelp API: geçersiz API key")
                    return []
                if resp.status == 429:
                    logger.warning("Yelp API: rate limit (5000/gün doldu)")
                    return []
                if resp.status != 200:
                    logger.warning(f"Yelp API HTTP {resp.status} — {sector}/{location}")
                    return []
                data = await resp.json()

            businesses = data.get("businesses", [])
            if not businesses:
                logger.info(f"Yelp: sonuç yok — {sector}/{location} (category={category})")
                return []

            leads: list[YelpLead] = []
            with_details = businesses[:fetch_details_count]
            without_details = businesses[fetch_details_count:]

            # 2. Fetch website URL for top results
            for biz in with_details:
                biz_id = biz.get("id", "")
                website = ""
                if biz_id:
                    try:
                        async with session.get(
                            YELP_DETAIL_URL.format(id=biz_id),
                            headers=headers,
                            timeout=aiohttp.ClientTimeout(total=10),
                        ) as dr:
                            if dr.status == 200:
                                detail = await dr.json()
                                website = detail.get("website", "") or ""
                    except Exception:
                        pass
                    await asyncio.sleep(0.15)

                leads.append(YelpLead(
                    name=biz.get("name", ""),
                    location=location,
                    sector=sector,
                    website=website,
                    phone=biz.get("display_phone", "") or biz.get("phone", ""),
                    rating=float(biz.get("rating", 0) or 0),
                    review_count=int(biz.get("review_count", 0) or 0),
                    yelp_url=biz.get("url", ""),
                ))

            # 3. Remaining results — no detail call (domain guess later)
            for biz in without_details:
                leads.append(YelpLead(
                    name=biz.get("name", ""),
                    location=location,
                    sector=sector,
                    phone=biz.get("display_phone", "") or biz.get("phone", ""),
                    rating=float(biz.get("rating", 0) or 0),
                    review_count=int(biz.get("review_count", 0) or 0),
                    yelp_url=biz.get("url", ""),
                ))

        logger.info(
            f"Yelp: {len(leads)} işletme bulundu — {sector}/{location} "
            f"(category={category}, website_fetched={len(with_details)})"
        )
        return leads

    except asyncio.TimeoutError:
        logger.warning(f"Yelp timeout — {sector}/{location}")
        return []
    except Exception as e:
        logger.warning(f"Yelp hata — {sector}/{location}: {e}")
        return []
