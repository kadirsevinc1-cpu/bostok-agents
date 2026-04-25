"""Sektör bazlı tasarım rehberi — saf veri, 0 token."""

_DESIGN_KB: dict[str, dict] = {
    "restoran": {
        "palette": ["#2C1810", "#F5E6D3", "#E8A87C", "#8B4513"],
        "palette_names": ["Koyu Kahve", "Krem", "Şeftali", "Amber"],
        "fonts": {"heading": "Playfair Display", "body": "Lato"},
        "style": "sıcak, davetkar, geleneksel-modern",
        "hero": "yemek fotoğrafı, akşam yemeği sahnesi",
        "sections": ["Menü", "Hakkımızda", "Rezervasyon", "Galeri", "İletişim"],
        "cta": "Rezervasyon Yap",
        "must_have": ["açılış saatleri", "adres+harita", "telefon", "menü PDF"],
    },
    "kafe": {
        "palette": ["#3D2B1F", "#F0E6D8", "#C8956C", "#6B4226"],
        "palette_names": ["Espresso", "Süt Kreması", "Karamel", "Kahve"],
        "fonts": {"heading": "Josefin Sans", "body": "Open Sans"},
        "style": "rahat, hipster, samimi",
        "hero": "kahve fincanı, latte art",
        "sections": ["Menü", "Hikayemiz", "Galeri", "İletişim"],
        "cta": "Menüyü İncele",
        "must_have": ["wifi bilgisi", "masa rezervasyonu", "günün kahvesi"],
    },
    "pastane": {
        "palette": ["#F8BBD9", "#FF80AB", "#3E2723", "#FFF8F0"],
        "palette_names": ["Pembe Şeker", "Fuşya", "Çikolata", "Krem"],
        "fonts": {"heading": "Dancing Script", "body": "Lato"},
        "style": "tatlı, zarif, davetkar",
        "hero": "pasta/börek fotoğrafı, sergileme",
        "sections": ["Ürünlerimiz", "Sipariş", "Hakkımızda", "İletişim"],
        "cta": "Sipariş Ver",
        "must_have": ["ürün galerisi", "sipariş formu", "teslim bilgisi"],
    },
    "berber": {
        "palette": ["#1A1A2E", "#C9A84C", "#E8E8E8", "#16213E"],
        "palette_names": ["Lacivert", "Altın", "Gümüş", "Gece Mavisi"],
        "fonts": {"heading": "Bebas Neue", "body": "Raleway"},
        "style": "maskülen, premium, vintage-modern",
        "hero": "berber sandalyesi, tıraş ürünleri",
        "sections": ["Hizmetler", "Fiyat Listesi", "Galeri", "Randevu", "İletişim"],
        "cta": "Randevu Al",
        "must_have": ["fiyat listesi", "online randevu", "çalışma saatleri"],
    },
    "guzellik_salonu": {
        "palette": ["#F8E8F0", "#E91E8C", "#2D2D2D", "#FAF0F5"],
        "palette_names": ["Pembe Tül", "Hot Pink", "Antrasit", "Krem"],
        "fonts": {"heading": "Cormorant Garamond", "body": "Montserrat"},
        "style": "feminen, lüks, zarif",
        "hero": "güzellik ürünleri, el bakımı",
        "sections": ["Hizmetler", "Fiyatlar", "Galeri", "Randevu", "İletişim"],
        "cta": "Randevu Al",
        "must_have": ["hizmet listesi+fiyat", "öncesi/sonrası galeri", "WhatsApp butonu"],
    },
    "doktor": {
        "palette": ["#E8F4FD", "#1976D2", "#FFFFFF", "#0D47A1"],
        "palette_names": ["Açık Mavi", "Tıbbi Mavi", "Beyaz", "Koyu Mavi"],
        "fonts": {"heading": "Merriweather", "body": "Source Sans Pro"},
        "style": "güvenilir, profesyonel, temiz",
        "hero": "muayenehane ortamı, güler yüz",
        "sections": ["Hizmetler", "Hakkımda", "Randevu", "İletişim"],
        "cta": "Randevu Al",
        "must_have": ["uzmanlık alanı", "cv/diploma", "randevu sistemi", "acil iletişim"],
    },
    "avukat": {
        "palette": ["#1A1A1A", "#C9A84C", "#F5F5F5", "#2C2C2C"],
        "palette_names": ["Siyah", "Altın", "Açık Gri", "Antrasit"],
        "fonts": {"heading": "Georgia", "body": "Georgia"},
        "style": "ciddi, güvenilir, otoriter",
        "hero": "adalet teması, kütüphane",
        "sections": ["Uzmanlık Alanları", "Hakkımızda", "Referanslar", "İletişim"],
        "cta": "Ücretsiz Danışma",
        "must_have": ["uzmanlık alanları", "baro sicil no", "referanslar", "gizlilik politikası"],
    },
    "muhasebe": {
        "palette": ["#003366", "#00A86B", "#F5F5F5", "#1A1A1A"],
        "palette_names": ["Lacivert", "Para Yeşili", "Açık Gri", "Antrasit"],
        "fonts": {"heading": "Nunito", "body": "Roboto"},
        "style": "güvenilir, düzenli, profesyonel",
        "hero": "grafik, hesaplama, iş ortamı",
        "sections": ["Hizmetler", "Hakkımızda", "Referanslar", "İletişim"],
        "cta": "Ücretsiz Analiz Al",
        "must_have": ["hizmet listesi", "vergi takvimi", "referanslar"],
    },
    "insaat": {
        "palette": ["#FF6B35", "#1A1A2E", "#F5F5F5", "#2C2C2C"],
        "palette_names": ["Turuncu", "Lacivert", "Açık Gri", "Antrasit"],
        "fonts": {"heading": "Oswald", "body": "Open Sans"},
        "style": "güçlü, dinamik, profesyonel",
        "hero": "tamamlanmış proje fotoğrafı",
        "sections": ["Projeler", "Hizmetler", "Hakkımızda", "İletişim"],
        "cta": "Proje Teklifi Al",
        "must_have": ["proje galerisi", "referanslar", "lisans bilgisi"],
    },
    "emlak": {
        "palette": ["#1E3A5F", "#D4A017", "#F8F8F8", "#2C2C2C"],
        "palette_names": ["Lacivert", "Altın", "Beyaz", "Antrasit"],
        "fonts": {"heading": "Raleway", "body": "Open Sans"},
        "style": "premium, güven veren, modern",
        "hero": "güzel ev/daire fotoğrafı",
        "sections": ["İlanlar", "Hizmetler", "Hakkımızda", "İletişim"],
        "cta": "Ücretsiz Değerleme",
        "must_have": ["ilan listesi", "harita", "online form", "WhatsApp"],
    },
    "oto_servis": {
        "palette": ["#E63946", "#1D3557", "#F1FAEE", "#457B9D"],
        "palette_names": ["Kırmızı", "Lacivert", "Krem", "Çelik Mavisi"],
        "fonts": {"heading": "Roboto Condensed", "body": "Roboto"},
        "style": "dinamik, güvenilir, erkeksi",
        "hero": "servis ortamı, araç bakım",
        "sections": ["Hizmetler", "Hakkımızda", "Randevu", "İletişim"],
        "cta": "Randevu Al",
        "must_have": ["hizmet listesi+fiyat", "çalışma saatleri", "acil hat"],
    },
    "otel": {
        "palette": ["#2C3E50", "#F39C12", "#ECF0F1", "#1A252F"],
        "palette_names": ["Gece Mavisi", "Altın", "Kırık Beyaz", "Koyu Gece"],
        "fonts": {"heading": "Playfair Display", "body": "Open Sans"},
        "style": "lüks, huzurlu, misafirperver",
        "hero": "lobi ya da oda fotoğrafı",
        "sections": ["Odalar", "Hizmetler", "Galeri", "Rezervasyon", "İletişim"],
        "cta": "Oda Rezervasyonu Yap",
        "must_have": ["oda tipleri+fiyat", "fotoğraf galerisi", "online rezervasyon", "konum"],
    },
    "spor_salonu": {
        "palette": ["#FF4500", "#1A1A1A", "#F5F5F5", "#FF6B35"],
        "palette_names": ["Turuncu Ateş", "Siyah", "Beyaz", "Canlı Turuncu"],
        "fonts": {"heading": "Oswald", "body": "Roboto"},
        "style": "enerjik, dinamik, motive edici",
        "hero": "egzersiz alanı, ekipman",
        "sections": ["Programlar", "Fiyatlar", "Eğitmenler", "Galeri", "İletişim"],
        "cta": "Ücretsiz Deneme Seansı",
        "must_have": ["ders/program takvimi", "üyelik fiyatları", "eğitmen profilleri"],
    },
    "default": {
        "palette": ["#2563EB", "#1E40AF", "#F8FAFC", "#1E293B"],
        "palette_names": ["Mavi", "Koyu Mavi", "Açık Gri", "Gece"],
        "fonts": {"heading": "Inter", "body": "Inter"},
        "style": "modern, temiz, profesyonel",
        "hero": "iş/hizmet fotoğrafı",
        "sections": ["Hizmetler", "Hakkımızda", "Referanslar", "İletişim"],
        "cta": "Bize Ulaşın",
        "must_have": ["iletişim bilgileri", "hizmet listesi"],
    },
}

_SECTOR_MAP: dict[str, list[str]] = {
    "restoran":       ["restoran", "restaurant", "lokanta", "kebap", "pide", "izgara"],
    "kafe":           ["kafe", "cafe", "coffee", "kahvaltı"],
    "pastane":        ["pastane", "fırın", "bakery", "börek", "tatlı", "pasta"],
    "berber":         ["berber", "barbershop", "erkek kuafor", "tıraş"],
    "guzellik_salonu":["güzellik", "beauty", "kuafor", "salon", "spa", "nail", "manikür"],
    "doktor":         ["doktor", "klinik", "hekim", "diş", "dental", "tıp", "sağlık", "psikolog"],
    "avukat":         ["avukat", "hukuk", "lawyer", "attorney", "hukuki"],
    "muhasebe":       ["muhasebe", "mali müşavir", "smmm", "accounting", "vergi"],
    "insaat":         ["inşaat", "yapı", "tadilat", "mimari", "müteahhit"],
    "emlak":          ["emlak", "gayrimenkul", "real estate", "kiralık", "satılık"],
    "oto_servis":     ["oto", "araba", "araç", "servis", "oto bakım", "lastik"],
    "otel":           ["otel", "hotel", "pansiyon", "konaklama", "apart"],
    "spor_salonu":    ["spor", "gym", "fitness", "egzersiz", "pilates", "yoga"],
}


def get_design_context(sector: str) -> dict:
    return _DESIGN_KB.get(sector, _DESIGN_KB["default"])


def detect_design_sector(text: str) -> str:
    text_lower = text.lower()
    for sector, keywords in _SECTOR_MAP.items():
        if any(kw in text_lower for kw in keywords):
            return sector
    return "default"


def format_design_hint(text: str) -> str:
    sector = detect_design_sector(text)
    ctx = get_design_context(sector)
    palette_str = ", ".join(
        f"{c} ({n})" for c, n in zip(ctx["palette"], ctx["palette_names"])
    )
    return (
        f"[Tasarım Rehberi — {sector}]\n"
        f"Renk Paleti: {palette_str}\n"
        f"Font: {ctx['fonts']['heading']} (başlık) / {ctx['fonts']['body']} (metin)\n"
        f"Stil: {ctx['style']}\n"
        f"Hero görseli: {ctx['hero']}\n"
        f"Zorunlu bölümler: {', '.join(ctx['sections'])}\n"
        f"Ana CTA: {ctx['cta']}\n"
        f"Mutlaka içermeli: {', '.join(ctx['must_have'])}\n"
    )
