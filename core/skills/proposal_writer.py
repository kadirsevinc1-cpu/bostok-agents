"""Otomatik teklif yazıcı — ilgi gösteren leade kişiselleştirilmiş fiyatlı teklif üretir."""
from loguru import logger

_PRICING = {
    "tr": {
        "currency": "₺",
        "basic":    ("Basic",    "15.000₺",  "5 sayfalı profesyonel web sitesi"),
        "standard": ("Standard", "25.000₺",  "10 sayfa + SEO optimizasyonu + kurumsal e-posta"),
        "premium":  ("Premium",  "45.000₺",  "E-ticaret + SEO + 6 ay teknik destek"),
    },
    "de": {
        "currency": "€",
        "basic":    ("Basic",    "499€",    "5-seitige professionelle Website"),
        "standard": ("Standard", "899€",    "10 Seiten + SEO-Optimierung + E-Mail-Einrichtung"),
        "premium":  ("Premium",  "1.499€",  "E-Commerce + SEO + 6 Monate Support"),
    },
    "en": {
        "currency": "$",
        "basic":    ("Basic",    "$599",    "5-page professional website"),
        "standard": ("Standard", "$999",    "10 pages + SEO optimization + business email"),
        "premium":  ("Premium",  "$1,799",  "E-commerce + SEO + 6 months support"),
    },
}

# Orta Doğu ve diğer İngilizce pazarlar için $ kullanan bölgeler
_DOLLAR_LOCATIONS = {
    "dubai", "abu dhabi", "riyadh", "jeddah", "doha", "kuwait", "muscat",
    "manama", "amman", "beirut", "cairo", "sharjah",
}


def _get_pricing(lang: str, location: str) -> dict:
    loc = location.lower()
    if any(d in loc for d in _DOLLAR_LOCATIONS):
        return _PRICING["en"]
    return _PRICING.get(lang, _PRICING["en"])


def _recommend_package(has_website: bool, sector: str) -> str:
    """Sektör ve duruma göre paket öner."""
    high_value = {"hukuk", "muhasebe", "klinik", "dis hekimi", "avukat", "otel",
                  "law firm", "dental", "solicitor", "zahnarzt", "rechtsanwalt"}
    sector_l = sector.lower()
    if any(h in sector_l for h in high_value):
        return "premium" if has_website else "standard"
    return "standard" if has_website else "basic"


async def write_proposal(
    lead_name: str,
    sector: str,
    location: str,
    has_website: bool,
    lang: str,
    reply_body: str,
    demo_url: str = "",
) -> tuple[str, str]:
    """Kişiselleştirilmiş teklif maili yaz. (subject, body) döndürür."""
    from core.llm_router import router

    pricing = _get_pricing(lang, location)
    rec = _recommend_package(has_website, sector)
    pkg_name, pkg_price, pkg_desc = pricing[rec]
    b_name, b_price, b_desc = pricing["basic"]
    s_name, s_price, s_desc = pricing["standard"]
    p_name, p_price, p_desc = pricing["premium"]

    lang_names = {"tr": "Türkçe", "en": "İngilizce", "de": "Almanca",
                  "nl": "Flemenkçe", "fr": "Fransızca"}
    lang_name = lang_names.get(lang, "İngilizce")

    situation = (
        "mevcut web sitelerini modernize etmek" if has_website
        else "sıfırdan profesyonel bir web sitesi kurmak"
    )

    demo_line = f"\nDemo siteniz: {demo_url}" if demo_url else ""

    prompt = f"""
{lang_name} dilinde "{lead_name}" isletmesine ({sector}, {location}) kisisellestirilmis web tasarim teklif maili yaz.

Musteri mesaji: {reply_body[:300]}

Durum: {situation}
Onerilmis paket: {pkg_name} — {pkg_price} ({pkg_desc})
{demo_line}

Tum paketleri listele:
- {b_name}: {b_price} — {b_desc}
- {s_name}: {s_price} — {s_desc}
- {p_name}: {p_price} — {p_desc}

Kuralllar:
- Musterinin mesajina dogrudan yanit ver, onceki yazismaya atif yap
- Onerilmis paketi one cikar ama digerleri de sunulabilir
- Teslimat suresi: Basic 5 is gunu, Standard 10 is gunu, Premium 15 is gunu
- %20 pesinat, teslimatta kalan odeme
- Profesyonel ve samimi ton — satis baskisi yapma
- Max 200 kelime, imza YAZMA
- Sadece mail metnini yaz, konu satiri ayri:
KONU: [konu satiri]
MAIL:
[mail metni]
"""

    try:
        result = await router.chat([{"role": "user", "content": prompt}], max_tokens=500)
        subject = f"Teklif: Web Sitesi — {lead_name}"
        body = result

        lines = result.strip().splitlines()
        mail_start = None
        for i, line in enumerate(lines):
            u = line.strip().upper()
            if u.startswith("KONU:"):
                subject = line.strip()[5:].strip()
            elif u.startswith("MAIL:"):
                mail_start = i + 1

        if mail_start is not None:
            body = "\n".join(lines[mail_start:]).strip()

        if len(body) < 30:
            return subject, ""

        signature = "\n\nSaygılar,\nKadir Sevinç - Bostok.dev\nhttps://bostok.dev"
        return subject, body + signature

    except Exception as e:
        logger.error(f"Teklif yazimi hatasi: {e}")
        return "", ""
