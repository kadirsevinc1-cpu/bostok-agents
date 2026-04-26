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
    base = """Sen Bostok.dev web ajansının Pazarlama agent'ısın.

Bostok.dev: Profesyonel web tasarım ve geliştirme ajansı. https://bostok.dev

Kurallar:
- Mesajlar profesyonel, samimi, spam olmayan tonda
- Max 120 kelime / mesaj
- Bostok.dev'i doğal tanıt — zorlamadan
- Her zaman net CTA ekle (https://bostok.dev)
- İmza: Kadir Sevinç — Bostok.dev"""
    return f"{profile_ctx}\n\n{base}" if profile_ctx else base


SYSTEM = _build_system()

LANG_NAMES = {"tr": "Türkçe", "en": "İngilizce", "de": "Almanca", "nl": "Flemenkçe", "fr": "Fransızca"}

SIGNATURE = "\n\nSaygılar,\nKadir Sevinç - Bostok.dev\nhttps://bostok.dev"

_WORKER_BASE = "https://bostok-demo.kadirsevinc1.workers.dev"
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

    async def loop(self):
        msg = await self.receive(timeout=1.0)
        if not msg:
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
        else:
            # Demo mod: şablon üret + gönderim simüle et
            result = await self._demo_campaign(sector, location, languages, has_leads=bool(leads))

        self.save_observation(
            f"Kampanya: {sector}/{location}: {str(result)[:200]}",
            importance=6.0
        )

        await self.send(AgentName.MANAGER, MessageType.RESULT, str(result))

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
            return f"Gunluk mail limiti doldu. {gmail.stats}"

        from core.skills.lead_scorer import sort_leads_by_score
        from core.skills.email_ab import pick_better_subject

        # Leadleri puana göre sırala — yüksek potansiyelli önce
        leads = sort_leads_by_score(leads)
        logger.info(f"Lead skorlama: {len(leads)} aktif lead")

        sent = skipped = no_email = 0

        for lead in leads:
            if not gmail.can_send():
                break
            if not lead.email:
                no_email += 1
                continue

            seo = None
            if lead.has_website and lead.website:
                try:
                    from integrations.seo_analyzer import analyze as seo_analyze
                    seo = await seo_analyze(lead.website)
                except Exception:
                    pass

            # Her dil için ayrı mail gönder (örn. Istanbul oteli → tr + en)
            for lang in (languages or ["tr"]):
                if not gmail.can_send():
                    break
                subject, body = await self._write_email(lead, lang, seo)
                body = await self._qa_email(subject, body, lang)
                if not body:
                    logger.warning(f"Mail kalite kontrolden gecemedi, atlandi: {lead.email} [{lang}]")
                    skipped += 1
                    continue

                # A/B konu satırı — ~100 token, daha yüksek açılma oranı
                better = await pick_better_subject(lead.name, sector, lang, body[:200])
                if better:
                    subject = better

                ok = await gmail.send(lead.email, subject, body, lead_info={
                    "name": lead.name, "sector": sector, "location": location, "lang": lang,
                })
                if ok:
                    sent += 1
                else:
                    skipped += 1
                await asyncio.sleep(8)  # spam önleme: mailler arası bekleme

        return (
            f"Kampanya tamamlandi [{sector}/{location}]:\n"
            f"- Gonderilen: {sent}\n"
            f"- Atlanan (zaten gonderildi/limit): {skipped}\n"
            f"- Email bulunamayan: {no_email}\n"
            f"- {gmail.stats}"
        )

    def _make_demo_url(self, lead, lang: str) -> str:
        import urllib.parse
        params = {
            "s": _ascii_param(lead.sector),
            "n": _ascii_param(lead.name),
            "c": _ascii_param(lead.location),
            "lang": lang,
        }
        if getattr(lead, "rating", None):
            params["r"] = str(lead.rating)
        if getattr(lead, "phone", None):
            params["p"] = lead.phone
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
        lang_name = LANG_NAMES.get(lang, lang)

        if lead.has_website:
            seo_detail = seo.for_email_prompt() if seo else ""
            offer = (
                "Web siteleri var AMA eski, yavaş veya mobil uyumsuz olabilir. "
                "Teklif: siteyi modernize etme, hız artırma, mobil uyumluluk, SEO iyileştirme. "
                "Ton: mevcut çalışmalarını takdir et, geliştirme fırsatı sun."
            )
            if seo_detail:
                offer += f" Kişiselleştirme için şu gerçek sorunları kullan: {seo_detail}"
        else:
            offer = (
                "Henüz web siteleri YOK — dijital dünyada görünmüyorlar. "
                "Teklif: sıfırdan profesyonel web sitesi yapımı. "
                "Ton: fırsatı vurgula, rakiplerinden geri kalmasın."
            )

        demo_url = self._make_demo_url(lead, lang)
        demo_url = await self._verify_demo_url(demo_url)

        if demo_url:
            demo_instruction = (
                f"Onemli: Mailde su demo linki dogal bir sekilde vurgula: {demo_url}\n"
                f"(\"Sizin icin bir demo hazirladim\" veya \"Nasil gorunebilecegini buradan gorebilirsiniz\" tarzinda)\n\n"
            )
        else:
            demo_instruction = ""

        prompt = (
            f"{lead.sector} sektöründeki \"{lead.name}\" isletmesine ({lead.location}) "
            f"{lang_name} dilinde profesyonel soguk e-posta yaz.\n\n"
            f"Durum: {offer}\n\n"
            f"{demo_instruction}"
            "Format:\n"
            "Konu: [kisa konu satiri]\n\n"
            "[Mail metni — max 130 kelime]\n\n"
            f"Dil kurallari: Mükemmel {lang_name} dil bilgisi kullan. "
            "Imla, noktalama ve gramer hatasi KESINLIKLE olmamali. "
            "Kurallar: isletme adini kullan, bostok.dev dogal tanit, "
            "sonda https://bostok.dev linki ver. İmza YAZMA, sona ekliyoruz."
        )
        # KB'den sektör + dil bilgisi çek
        try:
            from core.sector_kb import get_kb
            kb_ctx = get_kb().get_context(lead.sector, lead.location, lang)
            if kb_ctx:
                prompt = f"[Bilgi tabanı]\n{kb_ctx}\n\n" + prompt
        except Exception:
            pass
        result = await self.ask(prompt)
        subject = f"Web Siteniz Hakkinda — Bostok.dev"
        body = result

        lines = result.strip().splitlines()
        for i, line in enumerate(lines):
            if line.lower().startswith("konu:"):
                subject = line[5:].strip()
                body = "\n".join(lines[i + 1:]).strip()
                break

        body = body.rstrip() + SIGNATURE
        return subject, body

    # ── Mail kalite kontrolü ─────────────────────────────────────

    async def _qa_email(self, subject: str, body: str, lang: str) -> str:
        """
        Maili dil ve ton açısından kontrol et.
        Sorun varsa düzeltilmiş versiyonu döndür.
        Düzeltilemezse boş string döndür (mail gönderilmez).
        """
        from loguru import logger

        lang_name = LANG_NAMES.get(lang, lang)
        prompt = (
            f"Asagidaki soguk satis mailini {lang_name} dil kurallari acisindan denetle ve MUTLAKA duzelt.\n\n"
            f"KONU: {subject}\n\nMAIL:\n{body}\n\n"
            "Gorev:\n"
            f"1. {lang_name} imla ve gramer hatalarini duzelt (en onemli adim)\n"
            "2. Spam tetikleyici ifadeleri kaldir (BUYUK HARF, !!!, 'ucretsiz kazan' vb.)\n"
            "3. https://bostok.dev linki yoksa ekle\n"
            "4. Imzayı DOKUNMA, biz ekliyoruz\n"
            "5. 150 kelimeyi asiyorsa kisalt\n\n"
            "Yanit SADECE su formatta olmali, baska hicbir sey yazma:\n"
            "DURUM: ONAYLANDI\n"
            "DUZELTILMIS_MAIL:\n"
            "[duzeltilmis veya onaylanmis mail metni buraya — sadece body]"
        )

        try:
            result = await self.ask(prompt)

            # DUZELTILMIS_MAIL: etiketi ile ayristir
            marker = "DUZELTILMIS_MAIL:"
            if marker in result.upper():
                idx = result.upper().index(marker)
                corrected_body = result[idx + len(marker):].strip()
                if corrected_body and len(corrected_body) > 20:
                    if "ONAYLANDI" not in result.upper()[:idx]:
                        logger.info(f"Mail QA duzeltildi: {subject[:50]}")
                    return corrected_body

            # Marker yoksa orijinal gonder ama logla
            logger.warning(f"Mail QA format hatasi, orijinal gonderiliyor: {subject[:50]}")
            return body

        except Exception as e:
            logger.warning(f"Mail QA hata: {e} — orijinal gonderiliyor")
            return body

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
