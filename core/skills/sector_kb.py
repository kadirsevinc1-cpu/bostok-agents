"""
Sector Knowledge Base — sektöre özel terminoloji, istatistik, ton rehberi.
LLM kullanmaz (0 token). Prompt'a küçük context blok ekler.
"""

_KB: dict[str, dict] = {
    # ── Türkiye ───────────────────────────────────────────────────
    "restoran": {
        "stats": "Türkiye'deki restoranların %73'ünün web sitesi yok veya çok eski.",
        "pain": "online görünürlük yok, rezervasyon sistemi eksik, menü güncel değil",
        "tone": "samimi, yiyecek odaklı, lokal kültürü vurgula",
        "keywords": "menü, rezervasyon, sipariş, paket servis, özel gün",
    },
    "kafe": {
        "stats": "Kafe müşterilerinin %65'i mekanı sosyal medya veya Google üzerinden buluyor.",
        "pain": "sosyal medya bağlantısı yok, çalışma saatleri belirsiz, WiFi/atmosfer vurgulanmıyor",
        "tone": "rahat, samimi, yaşam tarzı odaklı",
        "keywords": "kahve, atmosfer, çalışma ortamı, canlı müzik, vegan",
    },
    "dis hekimi": {
        "stats": "Hastaların %68'i diş hekimini çevrimiçi araştırıyor; %54'ü online randevu bekliyor.",
        "pain": "online randevu yok, hizmet listesi belirsiz, hasta yorumları görünmüyor",
        "tone": "profesyonel, güven verici, teknik ama anlaşılır",
        "keywords": "implant, diş beyazlatma, ortodonti, randevu, ağız sağlığı, estetik",
    },
    "avukat": {
        "stats": "Hukuki hizmet arayanların %74'ü Google'da arama yapıyor.",
        "pain": "uzmanlık alanı belirsiz, güvenilirlik kanıtlanamıyor, iletişim zor",
        "tone": "ciddi, güven verici, uzmanlığı ön plana çıkar",
        "keywords": "hukuki danışmanlık, dava, sözleşme, arabuluculuk, ücretsiz görüşme",
    },
    "guzellik salonu": {
        "stats": "Online randevu sunan güzellik salonları %40 daha fazla müşteri çekiyor.",
        "pain": "portföy gösterilemiyor, randevu sistemi manuel, öncesi/sonrası yok",
        "tone": "şık, modern, estetik odaklı, kadına hitap",
        "keywords": "saç kesimi, makyaj, cilt bakımı, kalıcı makyaj, randevu, kampanya",
    },
    "oto servis": {
        "stats": "Oto servis müşterilerinin %61'i işletmeyi Google'da buluyor.",
        "pain": "fiyat şeffaflığı yok, online randevu yok, hizmet listesi belirsiz",
        "tone": "güvenilir, teknik ama sade, fiyat/hız odaklı",
        "keywords": "periyodik bakım, lastik, fren, motor, servis randevusu, oto ekspertiz",
    },
    "emlakci": {
        "stats": "Alıcıların %95'i ev ararken interneti kullanıyor; %67'si site yoksa güvensiz buluyor.",
        "pain": "portföy güncel değil, iletişim butonu yok, arama/filtreleme yok",
        "tone": "profesyonel, güven verici, fırsat odaklı",
        "keywords": "satılık, kiralık, yatırım, değerleme, proje, tapu",
    },
    "otel": {
        "stats": "Otel rezervasyonlarının %57'si mobil cihazlardan; %43'ü site yoksa başka oteli seçiyor.",
        "pain": "rezervasyon sistemi yok, galeri yetersiz, fiyatlar görünmüyor",
        "tone": "davetkar, deneyim odaklı, görseller çok önemli",
        "keywords": "rezervasyon, oda tipleri, konum, spa, kahvaltı dahil, erken rezervasyon",
    },
    "spor salonu": {
        "stats": "Spor salonu üyelerinin %78'i tesisin web sitesini ziyaret ediyor.",
        "pain": "üyelik bilgisi belirsiz, sınıf programı yok, ekip tanıtılmıyor",
        "tone": "enerjik, motive edici, sonuç odaklı",
        "keywords": "üyelik, personal trainer, grup dersi, beslenme, fitness, dönüşüm",
    },
    "muhasebe": {
        "stats": "KOBİ'lerin %61'i muhasebecisini tavsiye veya Google'dan buluyor.",
        "pain": "hizmet kapsamı belirsiz, iletişim formu yok, güven sembolleri eksik",
        "tone": "kurumsal, güvenilir, netlik vurgula",
        "keywords": "vergi, muhasebe, e-fatura, bilanço, SGK, SMMM",
    },
    "insaat": {
        "stats": "İnşaat firmalarının %80'inin portföy sitesi yok veya çok eski.",
        "pain": "proje portföyü gösterilemiyor, referans yok, iletişim zor",
        "tone": "güçlü, deneyim odaklı, görseller kritik",
        "keywords": "proje, referans, anahtar teslim, tadilat, ruhsat, yapı denetim",
    },
    # ── Almanya / DACH ────────────────────────────────────────────
    "restaurant": {
        "stats": "73% der Kunden prüfen die Speisekarte online vor dem Besuch.",
        "pain": "keine Online-Speisekarte, kein Reservierungssystem, schlechte Google-Sichtbarkeit",
        "tone": "einladend, authentisch, regionale Spezialitäten hervorheben",
        "keywords": "Speisekarte, Reservierung, Lieferung, Catering, Öffnungszeiten",
    },
    "zahnarzt": {
        "stats": "68% der Patienten recherchieren ihren Zahnarzt online.",
        "pain": "kein Online-Terminbuch, Leistungen unklar, keine Bewertungen sichtbar",
        "tone": "professionell, vertrauenswürdig, einfühlsam",
        "keywords": "Implantate, Zahnaufhellung, Kieferorthopädie, Termin, Mundgesundheit",
    },
    "fitnessstudio": {
        "stats": "78% der Mitglieder besuchen die Website vor der Anmeldung.",
        "pain": "Kursplan fehlt, Mitgliedschaftspreise unklar, kein Online-Check-in",
        "tone": "motivierend, energetisch, Ergebnisse betonen",
        "keywords": "Mitgliedschaft, Personal Training, Kursplan, Ernährung, Fitness",
    },
    # ── İngiltere / USA ───────────────────────────────────────────
    "dental clinic": {
        "stats": "68% of patients research their dentist online before booking.",
        "pain": "no online booking, services unclear, no patient reviews visible",
        "tone": "professional, reassuring, emphasize painless experience",
        "keywords": "implants, teeth whitening, orthodontics, emergency dental, NHS/private",
    },
    "law firm": {
        "stats": "74% of people seeking legal help start with a Google search.",
        "pain": "practice areas unclear, no trust signals, hard to contact",
        "tone": "authoritative, trustworthy, results-focused",
        "keywords": "consultation, case results, no win no fee, specialist, experience",
    },
    "real estate": {
        "stats": "95% of buyers use the internet in their home search.",
        "pain": "outdated listings, no contact form, poor mobile experience",
        "tone": "professional, opportunity-focused, local market expertise",
        "keywords": "listings, valuation, investment, neighborhood, mortgage calculator",
    },
    "gym": {
        "stats": "78% of gym members visit the website before signing up.",
        "pain": "class schedule missing, membership prices unclear, no virtual tour",
        "tone": "energetic, motivating, transformation-focused",
        "keywords": "membership, personal trainer, classes, nutrition, results, free trial",
    },
    "cleaning service": {
        "stats": "Cleaning businesses with websites get 3x more inquiries.",
        "pain": "no instant quote, no reviews, service areas unclear",
        "tone": "reliable, trustworthy, clean and simple",
        "keywords": "deep clean, regular cleaning, end of tenancy, commercial, eco-friendly",
    },
}


def get_sector_context(sector: str) -> str:
    """Sektör için kısa bağlam metni döndür — prompta eklenir."""
    kb = _find(sector)
    if not kb:
        return ""
    return (
        f"[Sektör Bağlamı] {kb['stats']} "
        f"Yaygın sorunlar: {kb['pain']}. "
        f"İçerik tonu: {kb['tone']}. "
        f"Anahtar kelimeler: {kb['keywords']}."
    )


def detect_sector(text: str) -> str:
    """Metinden sektörü tahmin et."""
    text_lower = text.lower()
    for key in _KB:
        if key in text_lower:
            return key
    # Partial match
    for key in _KB:
        words = key.split()
        if any(w in text_lower for w in words if len(w) > 4):
            return key
    return ""


def _find(sector: str) -> dict | None:
    sector_lower = sector.lower().strip()
    if sector_lower in _KB:
        return _KB[sector_lower]
    for key, val in _KB.items():
        if key in sector_lower or sector_lower in key:
            return val
    return None
