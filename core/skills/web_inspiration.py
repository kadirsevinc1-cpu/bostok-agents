"""
Web ilham bulucu — sektör bazlı tasarım trendleri, rakip analizi, referans örnekler.
Önce statik kuratif veri (0 token), opsiyonel Serper API ile canlı arama.
"""
from dataclasses import dataclass, field
from loguru import logger

_INSPIRATION_DB: dict[str, dict] = {
    "restoran": {
        "trends": [
            "Full-screen hero video (mutfak/yemek)",
            "Dark, warm renk paleti (#2C1810 baz)",
            "Büyük menü kartları, hover animasyonu",
            "Rezervasyon widgeti sabit (sticky) sidebar",
            "Instagram feed entegrasyonu",
            "Micro-interaction: yemek görseli hover'da büyür",
        ],
        "references": [
            "noma.dk — minimal, lüks fine dining",
            "dickeysbbq.com — enerji, canlı renkler",
            "eleven-madison-park.com — minimal, yüksek kalite fotoğraf",
        ],
        "must_avoid": [
            "Stok mutfak görseli (jenerik görünüm)",
            "Çok fazla animasyon (yavaşlatır)",
            "Mobilde kesilmiş menü",
        ],
        "keywords_seo": ["rezervasyon", "menü", "online sipariş", "paket servis"],
    },
    "kafe": {
        "trends": [
            "Warm earthy tones, kraft paper aesthetic",
            "Handwritten / script font (hero başlık)",
            "Before/after: çekirdek → fincan (story anlatımı)",
            "Günün kahvesi rotasyonu (dinamik içerik)",
            "Loyalty program vurgusu",
            "Harita widgeti (konum kritik)",
        ],
        "references": [
            "bluebottlecoffee.com — minimal, ürün odaklı",
            "stumptown.com — bold tipografi, craft feel",
        ],
        "must_avoid": ["Kahve bean stok fotoğraf klişe", "Yavaş loading arka plan video"],
        "keywords_seo": ["specialty coffee", "third wave", "pour over", "latte"],
    },
    "guzellik_salonu": {
        "trends": [
            "Pastel palette, feminen gradient",
            "Before/after slider (dönüşüm galerisi)",
            "Online randevu butonu hero'da büyük",
            "Ekip sayfası (güven oluşturur)",
            "Instagram galeri entegrasyonu",
            "Fiyat listesi accordion (collapse/expand)",
        ],
        "references": [
            "glamsquad.com — clean, profesyonel",
            "vagaro.com salon pages — çalışır randevu sistemi",
        ],
        "must_avoid": ["Jenerik kadın stok fotoğraf", "Karmaşık animasyon"],
        "keywords_seo": ["randevu", "saç boyama", "manikür", "cilt bakımı"],
    },
    "doktor": {
        "trends": [
            "Güven sinyalleri üst sırada (diplomalar, sertifikalar)",
            "Clean white/blue palette (steril hissi)",
            "Online randevu formu hero altında",
            "Google Reviews embed (sosyal kanıt)",
            "SSS bölümü (öne çıkan sorular)",
            "Acil hat telefon numarası her sayfada",
        ],
        "references": [
            "clevelandclinic.org — kurumsal güven",
            "zocdoc.com — ux odaklı randevu",
        ],
        "must_avoid": [
            "Gereksiz animasyon (ciddiyet azalır)",
            "Stok doktor-hasta görseli (güvensiz)",
        ],
        "keywords_seo": ["randevu al", "uzmanlık", "tedavi", "konsültasyon"],
    },
    "avukat": {
        "trends": [
            "Dark navy + gold palette (otorite)",
            "Davalar / başarı istatistikleri (sayaç animasyonu)",
            "Ücretsiz ilk görüşme CTA (dönüşüm artırır)",
            "Baro sicil numarası görünür yerde",
            "Blog / hukuki makaleler (SEO)",
            "Referans müvekkil logoları (B2B için)",
        ],
        "references": [
            "biglawfirm.com — kurumsal etki",
            "martindale.com — referans odaklı",
        ],
        "must_avoid": [
            "Adalet terazisi/tokmak klişesi (jenerik)",
            "Comic Sans / informal font",
        ],
        "keywords_seo": ["hukuki danışma", "dava", "avukat", "ücretsiz görüşme"],
    },
    "insaat": {
        "trends": [
            "Proje galerisi masonry layout (etkileyici)",
            "Tamamlanan proje sayacı (animasyonlu)",
            "3D render / before-after slider",
            "Canlı proje takip widget'ı",
            "Referans marka logoları carousel",
            "Sertifikalar ve lisanslar bölümü",
        ],
        "references": [
            "bechtel.com — büyük ölçek proje showcase",
            "skanska.com — sürdürülebilirlik vurgusu",
        ],
        "must_avoid": ["Hasar fotoğrafı (güven azalır)", "Uzun metin blokları"],
        "keywords_seo": ["inşaat", "tadilat", "müteahhit", "proje teslim"],
    },
    "emlak": {
        "trends": [
            "Full-screen harita + ilan overlay",
            "3D sanal tur embed (Matterport)",
            "Anında değerleme hesap makinesi",
            "Neighborhood score widget",
            "Video tur (drone çekimi)",
            "WhatsApp hızlı iletişim butonu",
        ],
        "references": [
            "zillow.com — ux, arama odaklı",
            "rightmove.co.uk — UK standart",
        ],
        "must_avoid": ["Çok küçük ilan kartları", "Yavaş harita yükleme"],
        "keywords_seo": ["kiralık", "satılık", "gayrimenkul", "değerleme"],
    },
    "oto_servis": {
        "trends": [
            "Koyu arka plan + kırmızı/turuncu accent",
            "Fiyat listesi şeffaf tablo",
            "Araç marka/model seçimi (ön filtre)",
            "Servis randevu formu (tarih picker)",
            "Müşteri yorumları carousel",
            "24/7 acil hat banner",
        ],
        "references": [
            "jiffy.com — hız vurgusu",
            "midas.com — şeffaf fiyatlandırma",
        ],
        "must_avoid": ["Çok fazla teknik jargon", "Mobilde küçük butonlar"],
        "keywords_seo": ["servis randevusu", "yağ değişimi", "lastik", "araç bakım"],
    },
    "default": {
        "trends": [
            "Hero bölümü: büyük başlık + net CTA",
            "Social proof (müşteri yorumları, logo bar)",
            "Hizmet kartları (icon + başlık + açıklama)",
            "İletişim bölümü her sayfada erişilebilir",
            "Mobil-first responsive tasarım",
            "Hız optimizasyonu (Core Web Vitals)",
        ],
        "references": [
            "stripe.com — clean, developer-friendly",
            "linear.app — modern SaaS UI",
        ],
        "must_avoid": ["Çok fazla renk", "Yavaş yüklenen görseller"],
        "keywords_seo": ["hizmet", "iletişim", "hakkımızda", "referanslar"],
    },
}

_ALIAS_MAP: dict[str, str] = {
    "restaurant": "restoran", "cafe": "kafe", "coffee": "kafe",
    "beauty salon": "guzellik_salonu", "beauty": "guzellik_salonu",
    "barbershop": "berber", "doktor": "doktor", "doctor": "doktor",
    "avukat": "avukat", "law firm": "avukat",
    "muhasebe": "muhasebe", "accounting": "muhasebe",
    "insaat": "insaat", "construction": "insaat",
    "emlak": "emlak", "real estate": "emlak",
    "oto servis": "oto_servis", "auto repair": "oto_servis",
}


@dataclass
class InspirationReport:
    sector: str
    trends: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    must_avoid: list[str] = field(default_factory=list)
    keywords_seo: list[str] = field(default_factory=list)
    live_results: list[dict] = field(default_factory=list)   # Serper'dan canlı sonuçlar

    def format_for_designer(self) -> str:
        lines = [f"[Web İlham Raporu — {self.sector}]"]
        if self.trends:
            lines.append("\nGüncel Tasarım Trendleri:")
            lines.extend(f"  • {t}" for t in self.trends)
        if self.references:
            lines.append("\nReferans Siteler:")
            lines.extend(f"  → {r}" for r in self.references)
        if self.must_avoid:
            lines.append("\nKaçınılacaklar:")
            lines.extend(f"  ✗ {a}" for a in self.must_avoid)
        if self.keywords_seo:
            lines.append(f"\nSEO Anahtar Kelimeler: {', '.join(self.keywords_seo)}")
        if self.live_results:
            lines.append("\nGüncel Web Araması:")
            for r in self.live_results[:3]:
                lines.append(f"  [{r.get('title','')}] {r.get('link','')}")
        return "\n".join(lines)


def _normalize_sector(text: str) -> str:
    t = text.lower().strip()
    if t in _INSPIRATION_DB:
        return t
    for alias, key in _ALIAS_MAP.items():
        if alias in t:
            return key
    return "default"


async def _serpapi_search(query: str) -> list[dict]:
    """SerpApi ile Google araması (serpapi.com)."""
    try:
        from config import settings
        api_key = getattr(settings, "serpapi_api_key", "")
        if not api_key:
            return []
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://serpapi.com/search.json",
                params={"q": query, "api_key": api_key, "engine": "google", "num": 5, "hl": "en"},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"SerpApi hata: {resp.status}")
                    return []
                data = await resp.json()
                return [
                    {
                        "title":   r.get("title", ""),
                        "link":    r.get("link", ""),
                        "snippet": r.get("snippet", ""),
                    }
                    for r in data.get("organic_results", [])[:5]
                ]
    except Exception as e:
        logger.debug(f"SerpApi arama hata: {e}")
        return []


async def _serper_search(query: str) -> list[dict]:
    """Serper.dev API ile web araması (SerpApi yoksa fallback)."""
    try:
        from config import settings
        api_key = getattr(settings, "serper_api_key", "")
        if not api_key:
            return []
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://google.serper.dev/search",
                json={"q": query, "num": 5},
                headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=8),
            ) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                return [
                    {"title": r.get("title", ""), "link": r.get("link", ""), "snippet": r.get("snippet", "")}
                    for r in data.get("organic", [])[:5]
                ]
    except Exception as e:
        logger.debug(f"Serper arama hata: {e}")
        return []


async def get_inspiration(sector: str, location: str = "") -> InspirationReport:
    """
    Sektör için tasarım ilhamı al.
    Önce statik DB (0 token), opsiyonel Serper ile canlı sonuçlar.
    """
    key = _normalize_sector(sector)
    db = _INSPIRATION_DB.get(key, _INSPIRATION_DB["default"])

    report = InspirationReport(
        sector       = sector,
        trends       = db["trends"],
        references   = db["references"],
        must_avoid   = db["must_avoid"],
        keywords_seo = db["keywords_seo"],
    )

    # Canlı arama: SerpApi önce, yoksa Serper fallback
    loc_suffix = f" {location}" if location else ""
    query = f"{sector} web site design 2024 best examples{loc_suffix}"
    live = await _serpapi_search(query) or await _serper_search(query)
    if live:
        report.live_results = live
        logger.info(f"Web ilham araması: {len(live)} sonuç — {query[:60]}")

    return report
