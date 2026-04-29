"""Location string'den UTC offset tahmini — DST göz ardı edilir."""
import datetime

# (anahtar kelimeler seti, UTC offset)
_RULES: list[tuple[frozenset, int]] = [
    # Türkiye: UTC+3
    (frozenset({
        "istanbul", "ankara", "izmir", "antalya", "bursa", "gaziantep", "adana",
        "mersin", "kayseri", "samsun", "trabzon", "denizli", "malatya", "sanliurfa",
        "erzurum", "tekirdag", "edirne", "sakarya", "ordu", "diyarbakir", "canakkale",
        "rize", "kahramanmaras", "corum", "kocaeli", "eskisehir", "konya", "hatay",
        "bodrum", "alanya", "kusadasi", "cappadocia", "safranbolu", "artvin", "amasya",
        "mardin", "mugla", "kirklareli", "duzce", "sivas", "kars", "bilecik", "kutahya",
        "bern", "graz", "turkey", "turkiye",
    }), 3),

    # Almanya, Avusturya, İsviçre, Hollanda, Belçika, Fransa, İspanya, İtalya,
    # İskandinavya (SW/NO/DK): UTC+1
    (frozenset({
        "berlin", "hamburg", "munich", "cologne", "frankfurt", "stuttgart", "nuremberg",
        "dresden", "leipzig", "bremen", "hannover", "dortmund", "dusseldorf",
        "vienna", "zurich", "amsterdam", "rotterdam", "the hague", "brussels",
        "antwerp", "ghent", "paris", "lyon", "nice", "bordeaux", "madrid", "barcelona",
        "rome", "milan", "florence", "stockholm", "gothenburg", "malmo", "oslo",
        "copenhagen", "germany", "deutschland", "austria", "netherlands", "belgium",
        "france", "spain", "italy", "sweden", "norway", "denmark",
    }), 1),

    # Finlandiya, Yunanistan, Güney Afrika, Romanya, Baltık, Mısır,
    # Ürdün, Lübnan: UTC+2
    (frozenset({
        "helsinki", "athens", "johannesburg", "cape town", "bucharest", "tallinn",
        "riga", "vilnius", "cairo", "alexandria", "amman", "beirut",
        "finland", "greece", "south africa", "romania",
    }), 2),

    # İngiltere, İrlanda: UTC+0
    (frozenset({
        "london", "manchester", "birmingham", "leeds", "glasgow", "liverpool",
        "sheffield", "bristol", "newcastle", "nottingham", "edinburgh", "cardiff",
        "dublin", "uk", "england", "scotland", "ireland",
    }), 0),

    # BAE, Umman: UTC+4
    (frozenset({
        "dubai", "abu dhabi", "sharjah", "ajman", "muscat",
    }), 4),

    # Suudi Arabistan, Kuveyt, Katar, Bahreyn, Irak: UTC+3
    (frozenset({
        "riyadh", "jeddah", "mecca", "medina", "dammam", "kuwait city", "doha",
        "manama", "baghdad",
    }), 3),

    # ABD Doğu: UTC-5
    (frozenset({
        "new york", "miami", "boston", "washington dc", "atlanta", "charlotte",
        "orlando", "tampa", "nashville", "new orleans", "detroit",
    }), -5),

    # ABD Merkez: UTC-6
    (frozenset({
        "chicago", "houston", "dallas", "san antonio", "austin", "minneapolis",
    }), -6),

    # ABD Dağ: UTC-7
    (frozenset({
        "phoenix", "denver", "las vegas",
    }), -7),

    # ABD Batı: UTC-8
    (frozenset({
        "los angeles", "san francisco", "seattle", "san diego", "san jose",
        "portland", "vancouver",
    }), -8),

    # Kanada Doğu: UTC-5
    (frozenset({
        "toronto", "montreal", "ottawa",
    }), -5),

    # Kanada Batı: UTC-7
    (frozenset({
        "calgary", "edmonton",
    }), -7),

    # Avustralya Doğu: UTC+10
    (frozenset({
        "sydney", "melbourne", "brisbane", "gold coast",
    }), 10),

    # Avustralya Batı: UTC+8
    (frozenset({
        "perth",
    }), 8),

    # Avustralya Güney: UTC+9
    (frozenset({
        "adelaide",
    }), 9),

    # Yeni Zelanda: UTC+12
    (frozenset({
        "auckland", "wellington",
    }), 12),

    # Hindistan: UTC+5
    (frozenset({
        "mumbai", "delhi", "bangalore", "hyderabad", "chennai", "india",
    }), 5),

    # Güneydoğu Asya: UTC+7/8
    (frozenset({
        "bangkok", "jakarta", "kuala lumpur", "singapore", "bali", "phuket",
    }), 7),
]

_DEFAULT = 0  # bilinmeyen → UTC kabul et


def get_utc_offset(location: str) -> int:
    loc = location.lower()
    for keywords, offset in _RULES:
        if any(kw in loc for kw in keywords):
            return offset
    return _DEFAULT


def is_business_hours(location: str, utc_now: datetime.datetime | None = None) -> bool:
    """Hedef lokasyonun yerel saatine göre Pzt-Cum 09:00-18:00 mi?"""
    if utc_now is None:
        utc_now = datetime.datetime.utcnow()
    if utc_now.weekday() >= 5:
        return False
    offset = get_utc_offset(location)
    local_hour = (utc_now.hour + offset) % 24
    return 9 <= local_hour < 18
