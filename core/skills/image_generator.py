"""
Görsel üretici — Pollinations.ai (ücretsiz, API key yok) + Pexels stok görseller.
Sektöre uygun hero, hizmet ve arka plan görselleri üretir/bulur.
"""
import asyncio
import urllib.parse
from dataclasses import dataclass, field
from loguru import logger

POLLINATIONS_BASE = "https://image.pollinations.ai/prompt"

_SECTOR_PROMPTS: dict[str, dict] = {
    "restoran": {
        "hero":     "elegant restaurant interior warm lighting food photography professional",
        "service":  "delicious gourmet food plate restaurant menu professional photo",
        "bg":       "restaurant wooden table bokeh warm ambiance",
    },
    "kafe": {
        "hero":     "cozy cafe interior latte art coffee cup natural light",
        "service":  "specialty coffee pour over cafe menu professional",
        "bg":       "coffee beans wooden background minimal",
    },
    "pastane": {
        "hero":     "beautiful bakery pastry display elegant cakes professional photography",
        "service":  "fresh croissants pastries bakery counter",
        "bg":       "flour dusted wooden table baking ingredients",
    },
    "berber": {
        "hero":     "modern barbershop interior vintage barber chair professional studio lighting",
        "service":  "professional barber haircut razor shave close up",
        "bg":       "barbershop tools scissors comb dark moody",
    },
    "guzellik_salonu": {
        "hero":     "luxury beauty salon interior elegant pink white modern",
        "service":  "professional makeup artist beauty treatment spa",
        "bg":       "beauty products cosmetics flat lay minimal",
    },
    "doktor": {
        "hero":     "modern medical clinic reception clean white professional",
        "service":  "doctor patient consultation professional medical",
        "bg":       "clean medical equipment stethoscope white background",
    },
    "avukat": {
        "hero":     "law office professional mahogany desk books sophisticated",
        "service":  "lawyer professional consultation legal documents",
        "bg":       "law books gavel dark wood professional",
    },
    "muhasebe": {
        "hero":     "modern accounting office professional team financial charts",
        "service":  "accountant financial report analysis professional",
        "bg":       "financial graphs calculator documents clean",
    },
    "insaat": {
        "hero":     "modern construction site crane architecture professional",
        "service":  "construction workers building modern architecture",
        "bg":       "architectural blueprint construction materials",
    },
    "emlak": {
        "hero":     "luxury modern house exterior golden hour real estate photography",
        "service":  "beautiful apartment interior modern real estate",
        "bg":       "city skyline aerial view modern buildings",
    },
    "oto_servis": {
        "hero":     "modern auto repair garage professional mechanic car service",
        "service":  "mechanic working on car engine professional",
        "bg":       "car parts tools mechanic workshop dark",
    },
    "otel": {
        "hero":     "luxury hotel lobby elegant chandelier professional interior",
        "service":  "luxury hotel room bed white linen professional",
        "bg":       "hotel pool terrace sunset luxury",
    },
    "spor_salonu": {
        "hero":     "modern gym fitness center equipment motivation professional",
        "service":  "personal trainer fitness workout professional",
        "bg":       "gym equipment weights dark moody",
    },
    "default": {
        "hero":     "modern professional business office interior clean minimal",
        "service":  "professional business team meeting modern office",
        "bg":       "abstract modern geometric background professional",
    },
}

_SECTOR_ALIASES: dict[str, str] = {
    "restaurant": "restoran", "cafe": "kafe", "coffee": "kafe",
    "bakery": "pastane", "barbershop": "berber", "barber": "berber",
    "beauty salon": "guzellik_salonu", "beauty": "guzellik_salonu",
    "doctor": "doktor", "clinic": "doktor", "dental": "doktor",
    "law firm": "avukat", "lawyer": "avukat",
    "accounting": "muhasebe", "muhasebe": "muhasebe",
    "construction": "insaat", "real estate": "emlak",
    "auto repair": "oto_servis", "oto": "oto_servis",
    "hotel": "otel", "gym": "spor_salonu", "fitness": "spor_salonu",
}


@dataclass
class ImageSet:
    hero_url: str = ""
    service_url: str = ""
    bg_url: str = ""
    source: str = "pollinations"
    errors: list[str] = field(default_factory=list)

    def html_snippet(self, project_name: str = "") -> str:
        lines = []
        if self.hero_url:
            lines.append(f'<!-- Hero görseli -->')
            lines.append(f'<img src="{self.hero_url}" alt="{project_name} hero" loading="lazy" style="width:100%;height:100%;object-fit:cover">')
        if self.service_url:
            lines.append(f'<!-- Hizmet görseli -->')
            lines.append(f'<img src="{self.service_url}" alt="Hizmetler" loading="lazy">')
        if self.bg_url:
            lines.append(f'<!-- Arka plan görseli -->')
            lines.append(f'<!-- bg: {self.bg_url} -->')
        return "\n".join(lines)


def _normalize_sector(text: str) -> str:
    t = text.lower().strip()
    if t in _SECTOR_PROMPTS:
        return t
    for alias, key in _SECTOR_ALIASES.items():
        if alias in t:
            return key
    return "default"


def _pollinations_url(prompt: str, width: int = 1280, height: int = 720, seed: int = 42) -> str:
    encoded = urllib.parse.quote(prompt + " --no text watermark logo")
    return f"{POLLINATIONS_BASE}/{encoded}?width={width}&height={height}&seed={seed}&model=flux&nologo=true"


async def generate_images(sector: str, project_name: str = "", style: str = "") -> ImageSet:
    """Sektöre uygun 3 görsel URL'si üret (Pollinations.ai, ücretsiz)."""
    key = _normalize_sector(sector)
    prompts = _SECTOR_PROMPTS.get(key, _SECTOR_PROMPTS["default"])

    # Style varsa prompt'a ekle
    style_suffix = f" {style}" if style else ""

    hero_prompt    = prompts["hero"] + style_suffix
    service_prompt = prompts["service"] + style_suffix
    bg_prompt      = prompts["bg"] + style_suffix

    if project_name:
        hero_prompt = f"{project_name} " + hero_prompt

    img_set = ImageSet(
        hero_url    = _pollinations_url(hero_prompt, 1280, 640, seed=1),
        service_url = _pollinations_url(service_prompt, 800, 600, seed=2),
        bg_url      = _pollinations_url(bg_prompt, 1920, 1080, seed=3),
        source      = "pollinations.ai",
    )
    logger.info(f"Görsel URL'leri üretildi: {sector} ({key}) — Pollinations.ai")
    return img_set


async def find_pexels_images(sector: str, count: int = 3) -> list[dict]:
    """
    Pexels API ile stok fotoğraf bul.
    Her dict: {url, photographer, width, height, alt}
    """
    try:
        from config import settings
        api_key = getattr(settings, "pexels_api_key", "")
        if not api_key:
            logger.debug("Pexels API key yok, Pollinations kullanılıyor")
            return []

        import aiohttp
        key = _normalize_sector(sector)
        query = _SECTOR_PROMPTS.get(key, _SECTOR_PROMPTS["default"])["hero"]
        # Sadece ilk 4 kelime — Pexels kısa sorgular tercih eder
        short_query = " ".join(query.split()[:4])

        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.pexels.com/v1/search",
                params={"query": short_query, "per_page": count, "orientation": "landscape"},
                headers={"Authorization": api_key},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"Pexels API hata: {resp.status}")
                    return []
                data = await resp.json()
                results = []
                for photo in data.get("photos", []):
                    results.append({
                        "url": photo["src"]["large2x"],
                        "url_medium": photo["src"]["medium"],
                        "photographer": photo.get("photographer", ""),
                        "alt": photo.get("alt", sector),
                        "width": photo.get("width", 1280),
                        "height": photo.get("height", 720),
                        "pexels_url": photo.get("url", ""),
                    })
                logger.info(f"Pexels: {len(results)} görsel bulundu — {short_query}")
                return results
    except Exception as e:
        logger.warning(f"Pexels hata: {e}")
        return []


async def get_best_images(sector: str, project_name: str = "", style: str = "") -> ImageSet:
    """
    Önce Pexels dene (gerçek fotoğraf), yoksa Pollinations (AI üretim).
    """
    pexels = await find_pexels_images(sector, count=3)

    if pexels:
        img_set = ImageSet(
            hero_url    = pexels[0]["url"],
            service_url = pexels[1]["url"] if len(pexels) > 1 else "",
            bg_url      = pexels[2]["url"] if len(pexels) > 2 else "",
            source      = "pexels.com",
        )
        logger.info(f"Pexels görselleri kullanılıyor: {sector}")
        return img_set

    return await generate_images(sector, project_name, style)
