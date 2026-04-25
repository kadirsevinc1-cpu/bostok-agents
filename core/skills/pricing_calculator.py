"""Fiyat hesaplayıcı — sektör, lokasyon ve özellik bazlı formül (0 token)."""
from dataclasses import dataclass, field


@dataclass
class PriceEstimate:
    currency: str
    base_price: int
    extras: dict[str, int] = field(default_factory=dict)
    total: int = 0
    monthly_maintenance: int = 0
    timeline_weeks: int = 2
    notes: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.total = self.base_price + sum(self.extras.values())

    def summary(self) -> str:
        lines = [f"Baz fiyat: {self.base_price:,} {self.currency}"]
        for name, price in self.extras.items():
            lines.append(f"+ {name}: +{price:,} {self.currency}")
        lines.append(f"TOPLAM: {self.total:,} {self.currency}")
        lines.append(f"Aylik bakim: {self.monthly_maintenance:,} {self.currency}/ay")
        lines.append(f"Tahmini sure: {self.timeline_weeks} hafta")
        if self.notes:
            lines.append("Not: " + " | ".join(self.notes))
        return "\n".join(lines)


# (currency, landing, corporate, ecommerce, app, (maint_low, maint_high))
_REGION_PRICES: dict[str, tuple] = {
    "tr": ("TL",  3500,  8000,  25000, 35000, (500,  1000)),
    "de": ("EUR",  600,  1500,   4000,  6000, (150,   250)),
    "uk": ("GBP",  700,  1800,   5000,  7000, (150,   300)),
    "us": ("USD",  800,  2000,   6000,  8000, (200,   400)),
    "ae": ("USD",  900,  2500,   7000,  9000, (200,   450)),
    "fr": ("EUR",  600,  1500,   4000,  6000, (150,   250)),
    "nl": ("EUR",  650,  1600,   4500,  6500, (150,   250)),
    "au": ("AUD",  900,  2200,   6000,  8000, (200,   400)),
    "ca": ("CAD",  900,  2200,   6000,  8000, (200,   400)),
}

_SITE_TYPES: dict[str, int] = {
    "landing":   0,
    "corporate": 1,
    "ecommerce": 2,
    "app":       3,
}

_SECTOR_MULTIPLIERS: dict[str, float] = {
    "doktor":   1.15,
    "avukat":   1.20,
    "muhasebe": 1.10,
    "insaat":   1.10,
    "emlak":    1.15,
    "otel":     1.20,
    "default":  1.00,
}

_EXTRA_FEATURES: dict[str, float] = {
    "iletisim formu":   0.10,
    "galeri":           0.10,
    "blog":             0.15,
    "cok dil":          0.20,
    "randevu sistemi":  0.15,
    "e-ticaret":        0.30,
    "odeme sistemi":    0.25,
    "uyelik sistemi":   0.25,
    "canli destek":     0.10,
    "harita":           0.05,
}

_TIMELINE_WEEKS: list[int] = [1, 2, 4, 6]  # landing / corporate / ecommerce / app


def estimate_price(
    region: str = "tr",
    site_type: str = "corporate",
    sector: str = "default",
    features: list[str] | None = None,
) -> PriceEstimate:
    region_key = region.lower()
    prices = _REGION_PRICES.get(region_key, _REGION_PRICES["tr"])
    currency, landing, corporate, ecommerce, app, maint_range = prices

    type_idx = _SITE_TYPES.get(site_type, 1)
    base = [landing, corporate, ecommerce, app][type_idx]

    multiplier = _SECTOR_MULTIPLIERS.get(sector, _SECTOR_MULTIPLIERS["default"])
    base = int(base * multiplier)

    extras: dict[str, int] = {}
    for feat in (features or []):
        feat_norm = feat.lower().replace("ı", "i").replace("ş", "s").replace("ç", "c")
        for feat_name, pct in _EXTRA_FEATURES.items():
            if feat_name in feat_norm and feat_name not in extras:
                extras[feat_name] = int(base * pct)
                break

    maint = int(sum(maint_range) / 2)
    weeks = _TIMELINE_WEEKS[type_idx]

    notes = []
    if multiplier > 1.0:
        notes.append(f"{sector} sektoru uzman carpani x{multiplier}")
    if region_key not in _REGION_PRICES:
        notes.append("Bilinmeyen bolge, TR fiyatlari kullanildi")

    return PriceEstimate(
        currency=currency,
        base_price=base,
        extras=extras,
        monthly_maintenance=maint,
        timeline_weeks=weeks,
        notes=notes,
    )


def detect_region(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ["almanya", "germany", "deutschland", "munchen", "berlin", "hamburg"]):
        return "de"
    if any(w in t for w in ["ingiltere", "london", "birmingham", "manchester", " uk ", "british"]):
        return "uk"
    if any(w in t for w in ["fransa", "france", "paris"]):
        return "fr"
    if any(w in t for w in ["hollanda", "amsterdam", "netherlands"]):
        return "nl"
    if any(w in t for w in ["avustralya", "australia", "sydney", "melbourne"]):
        return "au"
    if any(w in t for w in ["kanada", "canada", "toronto", "vancouver"]):
        return "ca"
    if any(w in t for w in ["america", "usa", "new york", "california", "texas"]):
        return "us"
    if any(w in t for w in ["dubai", "bae", "uae", "qatar", "katar", "riyadh"]):
        return "ae"
    return "tr"


def detect_site_type(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ["e-ticaret", "magaza", "shop", "online satis", "woocommerce", "urun sat"]):
        return "ecommerce"
    if any(w in t for w in ["uygulama", " app ", "platform", "web app", "mobil"]):
        return "app"
    if any(w in t for w in ["landing", "tek sayfa", "one page", "tanitim sayfasi"]):
        return "landing"
    return "corporate"


def extract_features(text: str) -> list[str]:
    found = []
    t = text.lower()
    feature_hints = {
        "iletisim formu":  ["iletisim formu", "contact form", "form"],
        "galeri":          ["galeri", "gallery", "fotograf", "resim"],
        "blog":            ["blog", "haber", "makale"],
        "cok dil":         ["cok dil", "multilingual", "almanca", "ingilizce", "fransizca"],
        "randevu sistemi": ["randevu", "appointment", "booking", "takvim"],
        "odeme sistemi":   ["odeme", "payment", "kredi karti", "stripe", "iyzico"],
        "canli destek":    ["canli destek", "live chat", "chatbot", "whatsapp"],
    }
    for feat, hints in feature_hints.items():
        if any(h in t for h in hints):
            found.append(feat)
    return found
