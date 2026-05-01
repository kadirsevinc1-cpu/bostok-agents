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

    lang_names = {"tr": "Turkish", "en": "English", "de": "German",
                  "nl": "Dutch", "fr": "French", "es": "Spanish",
                  "pt": "Portuguese", "it": "Italian", "pl": "Polish",
                  "ar": "Arabic", "sv": "Swedish"}
    lang_name = lang_names.get(lang, "English")

    situation = (
        "modernize their existing website" if has_website
        else "build a professional website from scratch"
    )

    demo_line = f"\nDemo site: {demo_url}" if demo_url else ""

    from config import settings as _cfg
    if _cfg.calendly_url:
        calendly_line = (
            f"\nBook a call: discuss the package in a free 15-min call: {_cfg.calendly_url}"
        )
    else:
        calendly_line = ""

    prompt = f"""
Write a personalized web design proposal email in {lang_name} for the business "{lead_name}" ({sector}, {location}).

Client message: {reply_body[:300]}

Situation: {situation}
Recommended package: {pkg_name} — {pkg_price} ({pkg_desc})
{demo_line}{calendly_line}

List all packages:
- {b_name}: {b_price} — {b_desc}
- {s_name}: {s_price} — {s_desc}
- {p_name}: {p_price} — {p_desc}

Rules:
- Reply directly to the client's message, reference the previous exchange
- Highlight the recommended package but mention others are available
- Delivery: Basic 5 business days, Standard 10 business days, Premium 15 business days
- 20% upfront, remainder on delivery
- Professional and genuine tone — no hard sell
- Max 200 words, do NOT write a sign-off
- Write only the email body with subject line on a separate line:
SUBJECT: [subject line]
BODY:
[email body]
"""

    try:
        result = await router.chat([{"role": "user", "content": prompt}], max_tokens=500)
        subject = f"Proposal: Website — {lead_name}"
        body = result

        lines = result.strip().splitlines()
        mail_start = None
        for i, line in enumerate(lines):
            u = line.strip().upper()
            if u.startswith("SUBJECT:"):
                subject = line.strip()[8:].strip()
            elif u.startswith("BODY:"):
                mail_start = i + 1

        if mail_start is not None:
            body = "\n".join(lines[mail_start:]).strip()

        if len(body) < 30:
            return subject, ""

        _sigs = {
            "tr": "\n\nSaygılar,\nKadir Sevinç - Bostok.dev\nhttps://bostok.dev",
            "en": "\n\nBest regards,\nKadir Sevinç - Bostok.dev\nhttps://bostok.dev",
            "de": "\n\nMit freundlichen Grüßen,\nKadir Sevinç - Bostok.dev\nhttps://bostok.dev",
            "nl": "\n\nMet vriendelijke groeten,\nKadir Sevinç - Bostok.dev\nhttps://bostok.dev",
            "fr": "\n\nCordialement,\nKadir Sevinç - Bostok.dev\nhttps://bostok.dev",
        }
        signature = _sigs.get(lang, _sigs["en"])
        return subject, body + signature

    except Exception as e:
        logger.error(f"Teklif yazimi hatasi: {e}")
        return "", ""
