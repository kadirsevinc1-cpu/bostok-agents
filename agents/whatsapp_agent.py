"""WhatsAppAgent — Green-API ile WhatsApp outreach kampanyası."""
import asyncio
from loguru import logger
from agents.base import BaseAgent
from core.message_bus import AgentName, MessageType, Message

LANG_NAMES = {"tr": "Türkçe", "en": "İngilizce", "de": "Almanca"}

SYSTEM = """You are the WhatsApp outreach specialist of Bostok.dev agency.
You write short, genuine, natural WhatsApp messages.
WhatsApp format: plain text, emoji-friendly, max 3 short paragraphs.
Never look like spam — give the feel of a real person reaching out."""


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
        if metadata.get("campaign_type") == "monthly":
            await self._handle_monthly_campaign(wa)
            return

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

    async def _handle_monthly_campaign(self, wa):
        from loguru import logger
        from core.monthly_wa_selector import select_monthly_wa_leads, record_monthly_wa_sent
        import datetime

        state = await wa.check_state()
        if state != "authorized":
            await self.send(AgentName.MANAGER, MessageType.RESULT,
                            f"WhatsApp bağlı değil (durum: {state}). Telefonu bağlayın.")
            return

        leads = select_monthly_wa_leads(top_n=3)
        if not leads:
            await self.send(AgentName.MANAGER, MessageType.RESULT,
                            "Aylık WA kampanyası: telefonu olan uygun lead bulunamadı.")
            return

        sent_leads = []
        skipped = 0

        for lead in leads:
            if not wa.can_send():
                logger.warning("WhatsApp günlük/toplam limit doldu, kampanya durdu")
                break
            text = await self._write_monthly_message(lead)
            ok = await wa.send(lead.phone, text)
            if ok:
                sent_leads.append(lead)
                try:
                    from core.lead_state import get_tracker, LeadStage
                    get_tracker().add_event(lead.email, "whatsapp_sent", "Aylık WA kampanyası")
                except Exception:
                    pass
            else:
                skipped += 1
            await asyncio.sleep(60)

        if sent_leads:
            now = datetime.datetime.now()
            record_monthly_wa_sent(now.year, now.month, sent_leads)

        names = ", ".join(l.name for l in sent_leads)
        result = (
            f"Aylık WhatsApp Kampanyası:\n"
            f"- Gönderilen: {len(sent_leads)} kişi ({names})\n"
            f"- Atlanan: {skipped}\n"
            f"- {wa.stats}"
        )
        self.save_observation(f"Aylık WA kampanya: {len(sent_leads)} gönderildi", 7.0)
        await self.send(AgentName.MANAGER, MessageType.RESULT, result)

    async def _write_monthly_message(self, lead) -> str:
        from core.user_profile import get_profile
        profile = get_profile()
        owner = profile.get("owner", {})

        stage_map = {
            "replied": "previously replied to our email and showed interest",
            "followed_up2": "received two emails, no reply yet",
            "followed_up": "received one follow-up email",
            "contacted": "received one email from us",
            "new": "first time we're reaching out",
        }
        context = stage_map.get(lead.stage, "potential client")

        prompt = (
            f'Write a Turkish WhatsApp message for the business "{lead.name}" '
            f"({lead.sector} sector, {lead.location}).\n\n"
            f"Context: This person {context}. We offer web development services.\n\n"
            f"Rules:\n"
            f"- Plain text, use emoji but don't overdo it\n"
            f"- Max 3 short paragraphs\n"
            f"- Genuine, don't look like spam\n"
            f"- More personal and natural tone than email\n"
            f"- Include link at the end: https://bostok.dev\n"
            f"- DO NOT write a sign-off, we add it separately"
        )
        result = await self.ask(prompt)
        signature = f"\n\n{owner.get('name', 'Kadir Sevinç')} — Bostok.dev\nhttps://bostok.dev"
        return result.strip() + signature

    async def _write_message(self, lead, lang: str) -> str:
        from core.user_profile import get_profile
        profile = get_profile()
        owner   = profile.get("owner", {})
        lang_name = LANG_NAMES.get(lang, lang)

        has_site = getattr(lead, "has_website", False)
        if has_site:
            offer = (
                "They have a website but it can be modernized — "
                "we want to help with mobile compatibility, speed and SEO."
            )
        else:
            offer = "They have no website yet — we build professional sites from scratch."

        prompt = (
            f'Write a WhatsApp message in {lang_name} for the business "{lead.name}" '
            f"({lead.sector} sector, {lead.location}).\n\n"
            f"Situation: {offer}\n\n"
            f"Rules:\n"
            f"- Plain text, use emoji but don't overdo it\n"
            f"- Max 3 short paragraphs\n"
            f"- Genuine, don't look like spam\n"
            f"- Include link at the end: https://bostok.dev\n"
            f"- DO NOT write a sign-off, we add it separately"
        )
        result = await self.ask(prompt)
        signature = f"\n\n{owner.get('name', 'Kadir Sevinç')} — Bostok.dev\nhttps://bostok.dev"
        return result.strip() + signature
