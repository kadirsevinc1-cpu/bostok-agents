"""
Pazarlama Agent — potansiyel müşteri bulur, çok dilde kişiselleştirilmiş mail gönderir.
Gmail yapılandırılmışsa gerçek mail atar; değilse şablon üretir.
"""
import asyncio
from agents.base import BaseAgent
from core.message_bus import AgentName, MessageType, Message


SYSTEM = """Sen Bostok.dev web ajansının Pazarlama agent'ısın.

Bostok.dev: Profesyonel web tasarım ve geliştirme ajansı. https://bostok.dev

Kurallar:
- Mesajlar profesyonel, samimi, spam olmayan tonda
- Max 120 kelime / mesaj
- Bostok.dev'i doğal tanıt — zorlamadan
- Her zaman net CTA ekle (https://bostok.dev)
- İmza: Kadir Şevinç — Bostok.dev"""

LANG_NAMES = {"tr": "Türkçe", "en": "İngilizce", "de": "Almanca", "nl": "Flemenkçe", "fr": "Fransızca"}

DEMO_BASE = "https://bostok-demo.kadirsevinc1.workers.dev"


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

        lang = languages[0] if languages else "tr"
        sent = skipped = no_email = 0

        for lead in leads:
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
            subject, body = await self._write_email(lead, lang, seo)

            # Kalite kontrolü — sorun varsa bir kez düzelt
            body = await self._qa_email(subject, body, lang)
            if not body:
                logger.warning(f"Mail kalite kontrolden gecemedi, atlandi: {lead.email}")
                skipped += 1
                continue

            ok = await gmail.send(lead.email, subject, body, lead_info={
                "name": lead.name, "sector": sector, "location": location,
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
        params = {"s": lead.sector, "n": lead.name, "c": lead.location, "lang": lang}
        if getattr(lead, "rating", None):
            params["r"] = str(lead.rating)
        if getattr(lead, "phone", None):
            params["p"] = lead.phone
        return f"{DEMO_BASE}/?{urllib.parse.urlencode(params, quote_via=urllib.parse.quote)}"

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
        prompt = (
            f"{lead.sector} sektöründeki \"{lead.name}\" isletmesine ({lead.location}) "
            f"{lang_name} dilinde profesyonel soguk e-posta yaz.\n\n"
            f"Durum: {offer}\n\n"
            f"Onemli: Mailde su demo linki dogal bir sekilde vurgula: {demo_url}\n"
            f"(\"Sizin icin bir demo hazirladim\" veya \"Nasil gorunebilecegini buradan gorebilirsiniz\" tarzinda)\n\n"
            "Format:\n"
            "Konu: [kisa konu satiri]\n\n"
            "[Mail metni — max 130 kelime]\n\n"
            "Kurallar: isletme adini kullan, bostok.dev dogal tanit, "
            "sonda https://bostok.dev linki ver, imza: Kadir Sevinc - Bostok.dev"
        )
        result = await self.ask(prompt)
        subject = f"Web Siteniz Hakkinda — Bostok.dev"
        body = result

        lines = result.strip().splitlines()
        for i, line in enumerate(lines):
            if line.lower().startswith("konu:"):
                subject = line[5:].strip()
                body = "\n".join(lines[i + 1:]).strip()
                break

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
            f"Asagidaki soguk satis mailini {lang_name} dil kurallari ve profesyonellik acisindan denetle.\n\n"
            f"Konu: {subject}\n\n{body}\n\n"
            "Kontrol listesi:\n"
            "1. Dil bilgisi ve imla hatasi var mi?\n"
            "2. Ton profesyonel ve samimi mi (agresif veya spam gibi degil)?\n"
            "3. https://bostok.dev linki var mi?\n"
            "4. Imza var mi (Kadir Sevinc - Bostok.dev)?\n"
            "5. 150 kelimeden kisa mi?\n"
            "6. Spam tetikleyici kelimeler var mi? (ucretsiz kazan, BUYUK HARF, !!! gibi)\n\n"
            "Yanit formati:\n"
            "DURUM: ONAYLANDI veya DUZELTILDI veya REDDEDILDI\n"
            "SORUNLAR: [buldugun sorunlari listele, yoksa 'yok']\n"
            "MAIL:\n[onaylanmis veya duzeltilmis mail metni — sadece body, konu satiri olmadan]"
        )

        try:
            result = await self.ask(prompt)
            lines = result.strip().splitlines()

            durum = ""
            mail_lines = []
            in_mail = False

            for line in lines:
                if line.upper().startswith("DURUM:"):
                    durum = line.split(":", 1)[1].strip().upper()
                elif line.upper().startswith("MAIL:"):
                    in_mail = True
                elif in_mail:
                    mail_lines.append(line)

            corrected_body = "\n".join(mail_lines).strip()

            if "REDDEDILDI" in durum:
                logger.warning(f"Mail QA reddetti: {subject[:50]}")
                return ""

            if corrected_body:
                if "DUZELTILDI" in durum:
                    logger.info(f"Mail QA duzeltildi: {subject[:50]}")
                return corrected_body

            # Format bozuksa orijinal body'yi koru
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
