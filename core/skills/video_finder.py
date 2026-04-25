"""
Video bulucu — Pexels stok video API (ücretsiz).
Sektöre uygun arka plan videosu URL'si döndürür.
AI video üretimi için ücretli API gerekmekte; bu skill ücretsiz stok video kullanır.
"""
import asyncio
from dataclasses import dataclass, field
from loguru import logger

_SECTOR_QUERIES: dict[str, list[str]] = {
    "restoran":        ["restaurant dining food", "chef cooking kitchen", "people eating restaurant"],
    "kafe":            ["coffee shop cafe", "barista making coffee", "cozy cafe"],
    "pastane":         ["bakery bread pastry", "baker making cake", "pastry shop"],
    "berber":          ["barbershop haircut", "barber shaving", "men grooming salon"],
    "guzellik_salonu": ["beauty salon spa", "makeup artist", "hair styling salon"],
    "doktor":          ["modern hospital clinic", "doctor patient consultation", "medical team"],
    "avukat":          ["law office professional", "lawyer business meeting", "justice court"],
    "muhasebe":        ["business finance office", "accountant working", "financial charts"],
    "insaat":          ["construction building", "architecture modern building", "workers construction site"],
    "emlak":           ["luxury house exterior", "real estate modern home", "apartment interior design"],
    "oto_servis":      ["car repair mechanic", "auto garage service", "car engine"],
    "otel":            ["luxury hotel lobby", "hotel pool resort", "hotel room interior"],
    "spor_salonu":     ["gym fitness workout", "people exercising gym", "personal training"],
    "default":         ["modern office business", "professional team meeting", "city skyline"],
}

_SECTOR_ALIASES: dict[str, str] = {
    "restaurant": "restoran", "cafe": "kafe", "coffee shop": "kafe",
    "bakery": "pastane", "barbershop": "berber", "barber shop": "berber",
    "beauty salon": "guzellik_salonu", "beauty": "guzellik_salonu",
    "doctor": "doktor", "clinic": "doktor", "dental clinic": "doktor",
    "law firm": "avukat", "lawyer": "avukat",
    "accounting": "muhasebe", "accounting firm": "muhasebe",
    "construction": "insaat", "real estate": "emlak",
    "auto repair": "oto_servis", "auto repair shop": "oto_servis",
    "hotel": "otel", "gym": "spor_salonu", "fitness": "spor_salonu",
}


@dataclass
class VideoResult:
    url: str = ""
    preview_url: str = ""        # küçük boyut / önizleme
    width: int = 1920
    height: int = 1080
    duration: int = 0            # saniye
    videographer: str = ""
    pexels_url: str = ""
    html_snippet: str = ""
    found: bool = False
    error: str = ""


def _normalize_sector(text: str) -> str:
    t = text.lower().strip()
    if t in _SECTOR_QUERIES:
        return t
    for alias, key in _SECTOR_ALIASES.items():
        if alias in t:
            return key
    return "default"


def _make_html_snippet(video: VideoResult) -> str:
    if not video.url:
        return ""
    return (
        f'<video autoplay muted loop playsinline '
        f'style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;z-index:0">\n'
        f'  <source src="{video.url}" type="video/mp4">\n'
        f'</video>\n'
        f'<!-- Video: {video.videographer} — Pexels.com -->'
    )


async def find_video(sector: str, orientation: str = "landscape") -> VideoResult:
    """Pexels API ile sektöre uygun stok video bul."""
    try:
        from config import settings
        api_key = getattr(settings, "pexels_api_key", "")
        if not api_key:
            return VideoResult(error="Pexels API key yok (.env: PEXELS_API_KEY)")

        import aiohttp
        key = _normalize_sector(sector)
        queries = _SECTOR_QUERIES.get(key, _SECTOR_QUERIES["default"])

        async with aiohttp.ClientSession() as session:
            for query in queries:
                async with session.get(
                    "https://api.pexels.com/videos/search",
                    params={
                        "query": query,
                        "per_page": 3,
                        "orientation": orientation,
                        "size": "medium",
                    },
                    headers={"Authorization": api_key},
                    timeout=aiohttp.ClientTimeout(total=12),
                ) as resp:
                    if resp.status != 200:
                        logger.warning(f"Pexels Video API hata: {resp.status}")
                        continue
                    data = await resp.json()
                    videos = data.get("videos", [])
                    if not videos:
                        continue

                    v = videos[0]
                    # En yüksek çözünürlüklü HD dosyayı seç
                    files = sorted(
                        v.get("video_files", []),
                        key=lambda f: f.get("width", 0), reverse=True,
                    )
                    hd = next((f for f in files if f.get("width", 0) >= 1280), files[0] if files else None)
                    sd = next((f for f in files if f.get("width", 0) <= 1280), None)

                    if not hd:
                        continue

                    result = VideoResult(
                        url           = hd.get("link", ""),
                        preview_url   = sd.get("link", "") if sd else hd.get("link", ""),
                        width         = hd.get("width", 1920),
                        height        = hd.get("height", 1080),
                        duration      = v.get("duration", 0),
                        videographer  = v.get("user", {}).get("name", ""),
                        pexels_url    = v.get("url", ""),
                        found         = True,
                    )
                    result.html_snippet = _make_html_snippet(result)
                    logger.info(
                        f"Pexels video bulundu: '{query}' — "
                        f"{result.width}x{result.height}, {result.duration}s"
                    )
                    return result

        return VideoResult(error=f"'{sector}' için video bulunamadi")

    except Exception as e:
        logger.warning(f"Pexels Video hata: {e}")
        return VideoResult(error=str(e))


def get_css_fallback_animation(sector: str) -> str:
    """
    Video yoksa CSS ile animasyonlu arka plan.
    Gradient + subtle animation — video kadar etkileyici olmasa da çalışır.
    """
    key = _normalize_sector(sector)
    gradients = {
        "restoran":        "#2C1810, #8B4513",
        "kafe":            "#3D2B1F, #6B4226",
        "guzellik_salonu": "#F8E8F0, #E91E8C",
        "doktor":          "#E8F4FD, #1976D2",
        "insaat":          "#FF6B35, #1A1A2E",
        "default":         "#1E3A5F, #2563EB",
    }
    colors = gradients.get(key, gradients["default"])
    return f"""<style>
.hero-animated-bg {{
  background: linear-gradient(135deg, {colors});
  background-size: 400% 400%;
  animation: gradientShift 8s ease infinite;
}}
@keyframes gradientShift {{
  0%   {{ background-position: 0% 50%; }}
  50%  {{ background-position: 100% 50%; }}
  100% {{ background-position: 0% 50%; }}
}}
</style>"""
