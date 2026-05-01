"""
Pazarlama Agent — potansiyel müşteri bulur, çok dilde kişiselleştirilmiş mail gönderir.
Gmail yapılandırılmışsa gerçek mail atar; değilse şablon üretir.
"""
import asyncio
from agents.base import BaseAgent
from core.message_bus import AgentName, MessageType, Message


def _build_system() -> str:
    from core.user_profile import get_context
    profile_ctx = get_context("marketing")
    base = """You are the Marketing agent of Bostok.dev web agency.

Bostok.dev: Professional web design and development agency. https://bostok.dev

Rules:
- Messages must be professional, genuine, non-spammy
- Max 120 words per message
- Introduce Bostok.dev naturally — never pushy
- Always include a clear CTA (https://bostok.dev)
- Sign-off: Kadir Sevinç — Bostok.dev"""
    return f"{profile_ctx}\n\n{base}" if profile_ctx else base


SYSTEM = _build_system()

LANG_NAMES = {"tr": "Türkçe", "en": "İngilizce", "de": "Almanca", "nl": "Flemenkçe", "fr": "Fransızca"}

# Her dil için doğru kapanış ifadesi
SIGNATURES = {
    "tr": "\n\nSaygılar,\nKadir Sevinç - Bostok.dev\nhttps://bostok.dev",
    "en": "\n\nBest regards,\nKadir Sevinç - Bostok.dev\nhttps://bostok.dev",
    "de": "\n\nMit freundlichen Grüßen,\nKadir Sevinç - Bostok.dev\nhttps://bostok.dev",
    "nl": "\n\nMet vriendelijke groeten,\nKadir Sevinç - Bostok.dev\nhttps://bostok.dev",
    "fr": "\n\nCordialement,\nKadir Sevinç - Bostok.dev\nhttps://bostok.dev",
}

# Demo link için dile göre hazır cümle (model "çevir" demek yerine direkt kullanır)
_DEMO_PHRASES = {
    "tr": ("Sizin için özel bir demo hazırladım", "Nasıl görünebileceğinizi buradan görebilirsiniz"),
    "en": ("I've prepared a demo site just for you", "See how your website could look"),
    "de": ("Ich habe eine Demo speziell für Sie vorbereitet", "Sehen Sie hier, wie Ihre Website aussehen könnte"),
    "nl": ("Ik heb een demo speciaal voor u gemaakt", "Zie hier hoe uw website eruit zou kunnen zien"),
    "fr": ("J'ai préparé une démo spécialement pour vous", "Voyez ici comment votre site pourrait ressembler"),
}

# Calendly için dile göre hazır cümle
_CALENDLY_PHRASES = {
    "tr": "Ücretsiz 15 dakikalık görüşme için",
    "en": "Schedule a free 15-minute call",
    "de": "Kostenloses 15-Minuten-Gespräch vereinbaren",
    "nl": "Plan een gratis gesprek van 15 minuten",
    "fr": "Planifier un appel gratuit de 15 minutes",
}

# Hizmet özeti her dilde hazır
_SERVICE_LINES = {
    "tr": "Web tasarım, SEO optimizasyonu, e-ticaret çözümleri ve kurumsal kimlik hizmetleri için bostok.dev",
    "en": "Web design, SEO optimization, e-commerce solutions and branding services at bostok.dev",
    "de": "Webdesign, SEO-Optimierung, E-Commerce-Lösungen und Corporate-Identity-Services auf bostok.dev",
    "nl": "Webdesign, SEO-optimalisatie, e-commerceoplossingen en huisstijldiensten op bostok.dev",
    "fr": "Conception web, optimisation SEO, solutions e-commerce et identité visuelle sur bostok.dev",
}

import re as _re

_STRIP_PATTERNS = [
    # İmza benzeri satırlar (tüm diller)
    _re.compile(r'(?i)^(saygılar|saygılarımla|best regards|kind regards|regards|sincerely|yours sincerely|warm regards|mit freundlichen gr[üu][ßs]en|freundliche gr[üu][ßs]e|mit besten gr[üu][ßs]en|cordialmente|cordialement|bien cordialement|vriendelijke groeten|met vriendelijke groeten)[,.\s]*$'),
    # İsim / ajans referansı
    _re.compile(r'(?i)kadir\s*sevin[cç]'),
    _re.compile(r'(?i)bostok\.dev'),
    _re.compile(r'https?://bostok\.dev\S*'),
    # Otomatik gönderim notu
    _re.compile(r'(?i)(bu (e-?)?mail|this (e-?)?mail|diese (e-?)?mail).{0,60}(otomatik|automat|agent|ajans)'),
    _re.compile(r'(?i)(otomatik|automat).{0,60}(gönder|sent|versand)'),
    # Ayraçlar
    _re.compile(r'^[-_]{3,}$'),
]


def _strip_auto_content(body: str) -> str:
    """LLM'nin yazdığı imzayı ve otomasyon notlarını gövdeden temizle."""
    lines = body.splitlines()
    cut = len(lines)
    for i in range(len(lines) - 1, max(len(lines) - 10, -1), -1):
        stripped = lines[i].strip()
        if not stripped:
            cut = i
            continue
        if any(p.search(stripped) for p in _STRIP_PATTERNS):
            cut = i
        else:
            break
    return "\n".join(lines[:cut]).rstrip()


def _clean_subject(subject: str) -> str:
    """Konu satırından yüzdelik oran ve açıklama parantezlerini temizle."""
    subject = _re.sub(r'\s*\([^)]{0,60}(%|açılma|rate|öneril)[^)]{0,60}\)', '', subject, flags=_re.IGNORECASE)
    subject = _re.sub(r'\s*\[[^\]]{0,60}(%|açılma|rate)[^\]]{0,60}\]', '', subject, flags=_re.IGNORECASE)
    return subject.strip()

_WORKER_BASE = "https://bostok-demo.kadirsevinc1.workers.dev"

# Sector keyword → Pexels category mapping (matches JS MAP keys)
_SECTOR_CAT_MAP: dict[str, str] = {
    "restoran": "food", "restaurant": "food", "kafe": "food", "cafe": "food",
    "pastane": "food", "bakery": "food", "catering": "food", "food": "food",
    "dis hekimi": "health", "dental": "health", "eczane": "health", "pharmacy": "health",
    "klinik": "health", "clinic": "health", "hastane": "health", "hospital": "health",
    "veteriner": "health", "spor salonu": "health", "gym": "health", "fitness": "health",
    "avukat": "legal", "law": "legal", "muhasebe": "legal", "accounting": "legal",
    "sigorta": "legal", "insurance": "legal", "hukuk": "legal", "notary": "legal",
    "guzellik": "beauty", "beauty": "beauty", "berber": "beauty", "barber": "beauty",
    "spa": "beauty", "tirnak": "beauty", "nail": "beauty", "friseur": "beauty",
    "kapsalon": "beauty", "coiffeur": "beauty",
    "emlak": "realestate", "real estate": "realestate", "estate agent": "realestate",
    "immobilien": "realestate", "mimar": "realestate", "insaat": "realestate",
    "tadilat": "realestate", "elektrikci": "realestate", "temizlik": "realestate",
    "nakliyat": "realestate", "tesisatci": "realestate", "renovation": "realestate",
    "oto servis": "auto", "auto repair": "auto", "autohaus": "auto", "car": "auto",
    "lastikci": "auto", "tire": "auto", "autowerkstatt": "auto",
    "okul": "education", "school": "education", "kurs": "education", "course": "education",
    "dans": "education", "muzik": "education", "surucu": "education", "etut": "education",
    "kindergarten": "education", "daycare": "education", "tutoring": "education",
    "otel": "hotel", "hotel": "hotel", "pansiyon": "hotel", "resort": "hotel",
    "yazilim": "tech", "software": "tech", "bilgisayar": "tech", "computer": "tech",
    "reklam": "tech", "fotograf": "tech", "matbaa": "tech", "print": "tech",
    "cicekci": "retail", "florist": "retail", "kuyumcu": "retail", "optik": "retail",
    "pet shop": "retail", "kuru temizleme": "retail", "dry clean": "retail",
    "fabrika": "industrial", "factory": "industrial", "imalat": "industrial",
    "sanayi": "industrial", "industrial": "industrial", "makine": "industrial",
    "warehouse": "industrial", "logistics": "industrial",
}
_DEMO_URL_CACHE = None   # startup'ta Netlify URL buraya yüklenir

_TR_TABLE = str.maketrans("şğüöıçŞĞÜÖİIÇ", "sguoicSGUOIIC")


def _ascii_param(s: str) -> str:
    """URL parametresi için Türkçe→ASCII dönüşümü + max 50 karakter."""
    return s.translate(_TR_TABLE)[:50]


def _get_demo_base() -> str:
    """Sırayla: Vercel cache → Netlify cache → Worker URL."""
    global _DEMO_URL_CACHE
    if _DEMO_URL_CACHE:
        return _DEMO_URL_CACHE

    from pathlib import Path
    import urllib.request

    def _reachable(url: str) -> bool:
        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=4) as r:
                return r.status < 400
        except Exception:
            return False

    # 1. Vercel (öncelikli — çok güvenilir)
    vercel_cache = Path("memory/vercel_site_url.txt")
    if vercel_cache.exists():
        url = vercel_cache.read_text(encoding="utf-8").strip()
        if url and _reachable(url):
            _DEMO_URL_CACHE = url
            return url

    # 2. Netlify
    netlify_cache = Path("memory/demo_site_url.txt")
    if netlify_cache.exists():
        url = netlify_cache.read_text(encoding="utf-8").strip()
        if url and _reachable(url):
            _DEMO_URL_CACHE = url
            return url

    # 3. Cloudflare Worker (her zaman açık fallback)
    return _WORKER_BASE


class MarketingAgent(BaseAgent):
    name = AgentName.MARKETING
    system_prompt = SYSTEM
    max_tokens = 2000

    def __init__(self):
        super().__init__()
        self._paused = False

    async def loop(self):
        msg = await self.receive(timeout=1.0)
        if not msg:
            return
        from core.message_bus import MessageType as MT
        if msg.type == MT.PAUSE:
            self._paused = True
            from loguru import logger
            logger.info("MarketingAgent duraklatildi (Manager komutu)")
            return
        if msg.type == MT.RESUME:
            self._paused = False
            from loguru import logger
            logger.info("MarketingAgent devam ettiriliyor (Manager komutu)")
            return
        if self._paused:
            from loguru import logger
            logger.debug("MarketingAgent duraklatildi, gorev atlaniyor")
            return
        await self._handle(msg)

    async def _handle(self, msg: Message):
        from loguru import logger

        logger.info(f"Pazarlama gorevi: {msg.content[:60]}")
        metadata = msg.metadata or {}
        sector = metadata.get("sector", "genel")
        location = metadata.get("location", "")
        languages = metadata.get("languages", ["tr", "en"])
        send_emails = metadata.get("send_emails", False)

        # Lead bul (Google Maps API varsa gerçek, yoksa boş)
        leads = await self._find_leads(sector, location)

        # Otomatik onay: eşik altında ise send_emails'i otomatik aç
        if not send_emails and leads:
            from core.user_profile import auto_approve_threshold
            if len(leads) <= auto_approve_threshold():
                logger.info(f"Otomatik onay: {len(leads)} lead ≤ eşik, kampanya başlatılıyor")
                send_emails = True

        if send_emails and leads:
            result = await self._run_campaign(leads, sector, location, languages)
            self.save_observation(
                f"Kampanya: {sector}/{location}: {str(result)[:200]}",
                importance=6.0
            )
            await self.send(AgentName.MANAGER, MessageType.RESULT, str(result))
        else:
            # Demo mod — sadece logla, Telegram'a gönderme
            reason = "Google Maps API key eksik" if not leads else "Email bulunamadi"
            logger.info(f"Demo mod [{sector}/{location}]: {reason}, bildirim atlanıyor")

    # ── Lead bulma ────────────────────────────────────────────────

    async def _find_leads(self, sector: str, location: str) -> list:
        from integrations.lead_finder import find_leads
        from config import settings
        api_key = getattr(settings, "google_maps_api_key", "")
        try:
            return await find_leads(sector, location, api_key)
        except Exception as e:
            from loguru import logger
            logger.warning(f"Lead finder hata: {e}")
            return []

    # ── Gerçek kampanya (Gmail + lead listesi) ────────────────────

    async def _run_campaign(self, leads: list, sector: str, location: str, languages: list) -> str:
        from integrations.gmail import get_gmail
        from loguru import logger

        gmail = get_gmail()
        if not gmail:
            return f"Gmail yapilandirilmamis — {len(leads)} lead bulundu ama mail atilamadi."
        if not gmail.can_send():
            await self.send(AgentName.MANAGER, MessageType.CAMPAIGN_STATUS,
                            f"mail_limit_hit:{sector}/{location}",
                            {"event": "mail_limit_hit", "sector": sector, "location": location})
            return f"Gunluk mail limiti doldu. {gmail.stats}"

        from core.skills.lead_scorer import sort_leads_by_score

        # Leadleri puana göre sırala — yüksek potansiyelli önce
        leads = sort_leads_by_score(leads)
        logger.info(f"Lead skorlama: {len(leads)} aktif lead")

        # İş saati kontrolü — hedef lokasyonun yerel saatine göre Pzt-Cum 09:00-18:00
        from core.timezone_utils import is_business_hours, get_utc_offset
        import datetime as _dt
        _now = _dt.datetime.utcnow()
        if not is_business_hours(location, _now):
            _offset = get_utc_offset(location)
            _local_hour = (_now.hour + _offset) % 24
            logger.info(
                f"Mesai saati disi [{location} UTC{_offset:+d} => yerel {_local_hour:02d}:xx "
                f"{_now.strftime('%a')}], kampanya ertelendi"
            )
            return f"Mesai saati disi — kampanya ertelendi [{sector}/{location}]"

        sent = skipped = no_email = 0
        _no_email_leads: list = []   # event-driven LinkedIn önerisi için
        from integrations.gmail import load_bounced
        bounced_set = load_bounced()

        for lead in leads:
            if not gmail.can_send():
                break
            if not lead.email:
                no_email += 1
                _no_email_leads.append(lead)
                continue

            # Erken çık — zaten gönderildi veya bounce listesinde
            if gmail.is_sent(lead.email):
                skipped += 1
                continue
            if lead.email.strip().lower() in bounced_set:
                skipped += 1
                continue

            seo = None
            if lead.has_website and lead.website:
                try:
                    from integrations.seo_analyzer import analyze as seo_analyze
                    seo = await seo_analyze(lead.website)
                except Exception:
                    pass

            lang = (languages or ["tr"])[0]
            if not gmail.can_send():
                break
            subject, body = await self._write_email(lead, lang, seo)
            if not body:
                logger.warning(f"Mail uretimi basarisiz, atlandi: {lead.email} [{lang}]")
                skipped += 1
                continue

            ok = await gmail.send(lead.email, subject, body, lead_info={
                "name": lead.name, "sector": sector, "location": location, "lang": lang,
                "phone": getattr(lead, "phone", ""),
                "has_website": lead.has_website,
            })
            if ok:
                sent += 1
                try:
                    from core.performance_tracker import record_sent as _perf_sent
                    _perf_sent(sector, location)
                except Exception:
                    pass
            else:
                skipped += 1
            await asyncio.sleep(45)

        # Tüm leadler atlandıysa (sıfır yeni gönderim) → tükendi olarak işaretle
        if sent == 0 and (skipped > 0 or no_email > 0):
            try:
                from core.campaign_state import mark_exhausted
                mark_exhausted(sector, location)
            except Exception:
                pass

        # Event-driven: 3+ email-bulunamayan lead varsa LinkedIn aramasını öner
        if no_email >= 3 and _no_email_leads:
            try:
                hint = (
                    f"💡 <b>Otomatik Öneri:</b> {no_email} lead için email bulunamadı "
                    f"({sector}/{location}).\n"
                    f"LinkedIn üzerinden ulaşmak ister misin?\n"
                    f"<code>/linkedin {_ascii_param(sector)} {_ascii_param(location)}</code>"
                )
                await self.send(AgentName.SYSTEM, MessageType.USER_NOTIFY, hint)
            except Exception:
                pass

        return (
            f"Kampanya tamamlandi [{sector}/{location}]:\n"
            f"- Gonderilen: {sent}\n"
            f"- Atlanan (zaten gonderildi/limit): {skipped}\n"
            f"- Email bulunamayan: {no_email}\n"
            f"- {gmail.stats}"
        )

    async def _make_demo_url(self, lead, lang: str) -> str:
        import urllib.parse
        params = {
            "s": _ascii_param(lead.sector),
            "n": _ascii_param(lead.name),
            "c": _ascii_param(lead.location),
            "lang": lang,
        }
        if getattr(lead, "rating", None):
            params["r"] = str(lead.rating)
        if getattr(lead, "review_count", None):
            params["rc"] = str(lead.review_count)
        if getattr(lead, "phone", None):
            params["p"] = lead.phone
        if getattr(lead, "website", None):
            params["w"] = "1" if lead.has_website else "0"

        # Pexels photo for about-visual
        try:
            from integrations.pexels_photos import get_sector_photo
            from config import settings as _cfg
            if _cfg.pexels_api_key:
                sec_raw = lead.sector.lower()
                cat = next(
                    (v for k, v in _SECTOR_CAT_MAP.items() if k in sec_raw or sec_raw in k),
                    "food",
                )
                photo = await get_sector_photo(cat, _cfg.pexels_api_key)
                if photo:
                    params["ph"] = photo
        except Exception:
            pass

        base = _get_demo_base()
        return f"{base}/?{urllib.parse.urlencode(params, quote_via=urllib.parse.quote)}"

    async def _verify_demo_url(self, url: str) -> str:
        """Demo URL'i test et — erişilemezse boş döndür (kırık link mail gitmesin)."""
        import aiohttp
        from loguru import logger
        try:
            async with aiohttp.ClientSession() as s:
                async with s.head(url, timeout=aiohttp.ClientTimeout(total=4), allow_redirects=True) as r:
                    if r.status < 400:
                        return url
                    logger.warning(f"Demo URL erişilemiyor ({r.status}), maile link eklenmeyecek")
        except Exception as e:
            logger.warning(f"Demo URL kontrol hata: {e} — maile link eklenmeyecek")
        return ""

    async def _write_email(self, lead, lang: str, seo=None) -> tuple[str, str]:
        """
        Mail yaz, dil/kalite denetle ve en iyi konu satırını seç — tek LLM çağrısında.
        """
        lang_name = LANG_NAMES.get(lang, lang)

        if lead.has_website:
            seo_detail = seo.for_email_prompt() if seo else ""
            offer = (
                "They HAVE a website but it may be outdated, slow, or not mobile-friendly. "
                "Offer: modernize the site, improve speed, mobile compatibility, SEO. "
                "Tone: appreciate their existing work, present an upgrade opportunity."
            )
            if seo_detail:
                offer += f" Use these real issues for personalization: {seo_detail}"
        else:
            offer = (
                "They have NO website — invisible in the digital world. "
                "Offer: build a professional website from scratch. "
                "Tone: highlight the opportunity, warn they're falling behind competitors."
            )

        demo_url = await self._make_demo_url(lead, lang)
        demo_url = await self._verify_demo_url(demo_url)

        demo_phrase_a, demo_phrase_b = _DEMO_PHRASES.get(lang, _DEMO_PHRASES["en"])
        if demo_url:
            demo_instruction = (
                f'Important: Naturally include this demo link in the email: {demo_url}\n'
                f'(e.g. "{demo_phrase_a}" or "{demo_phrase_b}")\n\n'
            )
        else:
            demo_instruction = ""

        from config import settings as _cfg
        calendly_phrase = _CALENDLY_PHRASES.get(lang, _CALENDLY_PHRASES["en"])
        if _cfg.calendly_url:
            calendly_instruction = (
                f'Add this exact line before the sign-off: "{calendly_phrase}: {_cfg.calendly_url}"\n'
            )
        else:
            calendly_instruction = ""

        service_line = _SERVICE_LINES.get(lang, _SERVICE_LINES["en"])

        # Geçmiş başarılı pattern'ları prompta ekle
        pattern_hint = ""
        try:
            from core.skills.skill_crystallizer import get_success_hints
            pattern_hint = get_success_hints(lead.sector, lang)
            if pattern_hint:
                pattern_hint = f"\n{pattern_hint}\nUse these patterns as inspiration for tone and subject.\n\n"
        except Exception:
            pass

        prompt = (
            f'Write a professional cold outreach email in {lang_name} for the business '
            f'"{lead.name}" ({lead.sector} sector, {lead.location}).\n\n'
            f"Situation: {offer}\n\n"
            f"{pattern_hint}"
            f"{demo_instruction}"
            f"{calendly_instruction}"
            f"STRICT LANGUAGE RULE: The ENTIRE email MUST be written in {lang_name} ONLY. "
            f"Not a single word in any other language. "
            f"Perfect grammar, spelling and punctuation for {lang_name}. "
            f"No spam trigger words, no ALL CAPS. "
            f"Use the business name naturally. Mention bostok.dev and include https://bostok.dev link. "
            f'Add this exact line before the sign-off: "{service_line}" '
            f"DO NOT write: name sign-off, greeting/closing salutation, automation notes, bot disclaimers, percentages. "
            f"Max 150 words.\n\n"
            f"Response ONLY in this format, nothing else:\n"
            f"KONU_A: [first subject line — straightforward]\n"
            f"KONU_B: [second subject line — curiosity-inducing]\n"
            f"SECILEN_KONU: [the one with higher open rate — subject text only, no explanation]\n"
            f"MAIL:\n"
            f"[email body in {lang_name}]"
        )

        # KB'den sektör + dil bilgisi çek
        try:
            from core.sector_kb import get_kb
            kb_ctx = get_kb().get_context(lead.sector, lead.location, lang)
            if kb_ctx:
                prompt = f"[Bilgi tabanı]\n{kb_ctx}\n\n" + prompt
        except Exception:
            pass

        # A/B geçmiş verisi — iyi çalışan konu pattern'leri
        try:
            from core.ab_tracker import get_prompt_hint
            ab_hint = get_prompt_hint(lead.sector, lang)
            if ab_hint:
                prompt = f"[A/B Geçmiş]\n{ab_hint}\n\n" + prompt
        except Exception:
            pass

        result = await self.ask(prompt)

        subject = f"Web Siteniz Hakkinda — Bostok.dev"
        body = result

        lines = result.strip().splitlines()
        mail_start = None
        for i, line in enumerate(lines):
            stripped = line.strip()
            upper = stripped.upper()
            if upper.startswith("SECILEN_KONU:"):
                subject = _clean_subject(stripped[len("SECILEN_KONU:"):].strip())
            elif upper.startswith("MAIL:"):
                mail_start = i + 1

        if mail_start is not None:
            body = "\n".join(lines[mail_start:]).strip()
        elif not any(l.strip().upper().startswith("SECILEN_KONU:") for l in lines):
            for i, line in enumerate(lines):
                if line.lower().startswith("konu:"):
                    subject = _clean_subject(line[5:].strip())
                    body = "\n".join(lines[i + 1:]).strip()
                    break

        if not body or len(body) < 20:
            return subject, ""

        body = _strip_auto_content(body)

        # Spam kontrolü — skoru yüksekse bir kez tekrar yaz
        from core.skills.spam_checker import spam_score
        score, issues = spam_score(body)
        if score >= 2:
            from loguru import logger as _log
            _log.warning(f"Spam skoru {score} [{lead.name}]: {issues} — yeniden yaziliyor")
            retry_prompt = (
                f"Rewrite the following email to remove spam triggers.\n"
                f"Problems: {'; '.join(issues)}\n"
                f"Keep the same language ({lang_name}), same message, but cleaner and more natural.\n"
                f"DO NOT write a sign-off. Output ONLY the email body.\n\n"
                f"Original:\n{body}"
            )
            try:
                rewritten = await self.ask(retry_prompt)
                if rewritten and len(rewritten.strip()) > 20:
                    body = _strip_auto_content(rewritten.strip())
            except Exception:
                pass

        body = body + SIGNATURES.get(lang, SIGNATURES["en"])
        return subject, body

    # ── Demo kampanya (Gmail yok / lead yok) ─────────────────────

    async def _demo_campaign(self, sector: str, location: str, languages: list, has_leads: bool) -> str:
        langs_str = ", ".join(LANG_NAMES.get(l, l) for l in languages)
        note = "(Google Maps API key eksik — ornek sablonlar)" if not has_leads else "(email bulunamadi — sablonlar)"
        prompt = (
            f"{location}'daki {sector} isletmeleri icin {langs_str} dillerinde "
            f"iki tip mail sablonu yaz:\n"
            f"1) Web sitesi OLMAYAN isletmeler icin (dijitale girin mesaji)\n"
            f"2) Web sitesi OLAN ama eski/kotu isletmeler icin (modernlesme teklifi)\n"
            f"Her tip ve dil icin ayri sablon. Max 100 kelime/sablon. "
            f"Format: ### [Tip] - [Dil] / Konu: ... / [metin]"
        )
        templates = await self.ask(prompt)
        return (
            f"Kampanya Sablonu [{sector}/{location}] {note}:\n\n"
            f"{templates}\n\n"
            f"NOT: Gercek mail gondermek icin .env'e GMAIL_USER ve GMAIL_APP_PASSWORD ekleyin."
        )
