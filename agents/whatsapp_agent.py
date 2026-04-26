"""WhatsAppAgent — Green-API ile WhatsApp outreach kampanyası."""
import asyncio
from loguru import logger
from agents.base import BaseAgent
from core.message_bus import AgentName, MessageType, Message

LANG_NAMES = {"tr": "Türkçe", "en": "İngilizce", "de": "Almanca"}

SYSTEM = """Sen Bostok.dev ajansının WhatsApp outreach uzmanısın.
Kısa, samimi, doğal WhatsApp mesajları yazarsın.
WhatsApp formatı: plain text, emoji destekli, max 3 kısa paragraf.
Asla spam gibi görünme — gerçek bir insandan gelen mesaj hissi ver."""


class WhatsAppAgent(BaseAgent):
    name = AgentName.WHATSAPP
    system_prompt = SYSTEM
    max_tokens = 500

    async def loop(self):
        msg = await self.receive(timeout=1.0)
        if not msg:
            return
        await self._handle(msg)

    async def _handle(self, msg: Message):
        from integrations.whatsapp import get_whatsapp
        wa = get_whatsapp()
        if not wa:
            await self.send(AgentName.MANAGER, MessageType.RESULT,
                            "WhatsApp yapılandırılmamış (GREENAPI_INSTANCE_ID eksik).")
            return

        metadata = msg.metadata or {}
        sector    = metadata.get("sector", "genel")
        location  = metadata.get("location", "")
        languages = metadata.get("languages", ["tr"])

        state = await wa.check_state()
        if state != "authorized":
            await self.send(AgentName.MANAGER, MessageType.RESULT,
                            f"WhatsApp bağlı değil (durum: {state}). Telefonu bağlayın.")
            return

        leads = await self._find_leads(sector, location)
        phone_leads = [l for l in leads if getattr(l, "phone", None)]

        if not phone_leads:
            await self.send(AgentName.MANAGER, MessageType.RESULT,
                            f"Telefon numarası olan lead bulunamadı: {sector}/{location}")
            return

        sent = skipped = 0
        from core.performance_tracker import record_sent as perf_sent

        for lead in phone_leads:
            if not wa.can_send():
                break
            for lang in languages:
                if not wa.can_send():
                    break
                text = await self._write_message(lead, lang)
                ok = await wa.send(lead.phone, text)
                if ok:
                    sent += 1
                    perf_sent(sector, location)
                else:
                    skipped += 1
                # WhatsApp ban önleme: mail'den daha uzun bekleme
                await asyncio.sleep(45)

        result = (
            f"WhatsApp Kampanyası [{sector}/{location}]:\n"
            f"- Gönderilen: {sent}\n"
            f"- Atlanan: {skipped}\n"
            f"- {wa.stats}"
        )
        self.save_observation(f"WA kampanya: {sector}/{location} → {sent} gönderildi", 6.0)
        await self.send(AgentName.MANAGER, MessageType.RESULT, result)

    async def _find_leads(self, sector: str, location: str) -> list:
        from integrations.lead_finder import find_leads
        from config import settings
        try:
            return await find_leads(sector, location, getattr(settings, "google_maps_api_key", ""))
        except Exception as e:
            logger.warning(f"WA lead finder hata: {e}")
            return []

    async def _write_message(self, lead, lang: str) -> str:
        from core.user_profile import get_profile
        profile = get_profile()
        owner   = profile.get("owner", {})
        lang_name = LANG_NAMES.get(lang, lang)

        has_site = getattr(lead, "has_website", False)
        if has_site:
            offer = (
                f"Web siteleri var ama modernize edilebilir — "
                f"mobil uyumluluk, hız, SEO konularında yardım sunmak istiyoruz."
            )
        else:
            offer = "Henüz web siteleri yok — sıfırdan profesyonel site yapıyoruz."

        prompt = (
            f"{lead.sector} sektöründeki \"{lead.name}\" işletmesine "
            f"({lead.location}) {lang_name} dilinde WhatsApp mesajı yaz.\n\n"
            f"Durum: {offer}\n\n"
            f"Kurallar:\n"
            f"- Plain text, emoji kullan ama abartma\n"
            f"- Max 3 kısa paragraf\n"
            f"- Samimi, spam gibi görünme\n"
            f"- Sonuna link ekle: https://bostok.dev\n"
            f"- İmza: {owner.get('name', 'Kadir')} — {owner.get('agency', 'Bostok.dev')}\n"
            f"- İmza YAZMA, sona ekliyoruz"
        )
        result = await self.ask(prompt)
        signature = f"\n\n{owner.get('name', 'Kadir Sevinç')} — Bostok.dev\nhttps://bostok.dev"
        return result.strip() + signature
