"""InboxWatcher — Gmail inbox'ı 5 dakikada bir kontrol eder, bizim outreach maillerimize gelen yanıtları Telegram'a bildirir."""
import asyncio
from loguru import logger
from agents.base import BaseAgent
from core.message_bus import AgentName, MessageType, Message, bus


class InboxWatcherAgent(BaseAgent):
    name = AgentName.INBOX_WATCHER
    system_prompt = "Inbox takip agent"
    max_tokens = 100

    async def loop(self):
        from integrations.gmail_reader import get_reader

        reader = get_reader()
        if not reader:
            await asyncio.sleep(60)
            return

        loop = asyncio.get_running_loop()
        try:
            replies = await loop.run_in_executor(None, reader.check_replies)
        except Exception as e:
            logger.error(f"Inbox kontrol hatasi: {e}")
            await asyncio.sleep(300)
            return

        for reply in replies:
            # Bounce / teslimat hatası mı?
            from integrations.gmail import is_bounce, record_bounce
            if is_bounce(reply.from_email):
                # Orijinal alıcıyı sent_info'dan çıkar ve blacklist'e ekle
                original_to = reply.sent_info.get("to", "")
                if original_to:
                    record_bounce(original_to)
                    try:
                        from core.lead_state import get_tracker, LeadStage
                        get_tracker().update(original_to, LeadStage.BOUNCED, f"Bounce from: {reply.from_email}")
                    except Exception:
                        pass
                logger.info(f"Bounce tespit edildi, blackliste eklendi: {original_to} (gonden: {reply.from_email})")
                continue

            sent = reply.sent_info
            sector = sent.get("sector", "")
            location = sent.get("location", "")
            lead_name = sent.get("name", "")

            # Niyeti tespit et (0 token)
            from core.skills.reply_analyzer import analyze_reply
            analysis = analyze_reply(reply.body, reply.subject)
            intent_emoji = {
                "ready":       "🔥",
                "meeting":     "📅",
                "interested":  "✨",
                "question":    "❓",
                "negative":    "👎",
                "unsubscribe": "🚫",
                "spam":        "🗑️",
                "unknown":     "🤷",
            }.get(analysis.intent.value, "📧")

            if analysis.intent.value == "spam":
                logger.info(f"Spam yanit atlanıyor: {reply.from_email}")
                continue

            # Lead state güncelle
            try:
                from core.lead_state import get_tracker, LeadStage
                tracker = get_tracker()
                if analysis.intent.value == "unsubscribe":
                    tracker.update(reply.from_email, LeadStage.UNSUBSCRIBED, reply.subject[:80])
                else:
                    tracker.update(reply.from_email, LeadStage.REPLIED,
                                   f"{analysis.intent.value}: {reply.subject[:60]}")
            except Exception:
                pass

            # KB'ye pattern kaydet
            try:
                from core.sector_kb import get_kb
                lang = reply.sent_info.get("lang", "tr")
                positive_intents = {"ready", "meeting", "interested"}
                negative_intents = {"negative", "unsubscribe"}
                if analysis.intent.value in positive_intents:
                    desc = (f"{sector}/{location}: '{analysis.summary[:100]}' — "
                            f"niyet={analysis.intent.value}")
                    get_kb().add_pattern("positive", sector, location, lang, desc)
                elif analysis.intent.value in negative_intents:
                    desc = (f"{sector}/{location}: '{analysis.summary[:100]}' — "
                            f"niyet={analysis.intent.value}")
                    get_kb().add_pattern("negative", sector, location, lang, desc)
            except Exception:
                pass

            if analysis.intent.value == "unsubscribe":
                logger.info(f"Abonelik iptali: {reply.from_email}")

            notify = (
                f"{intent_emoji} <b>Yeni Yanit!</b> [ID: {reply.reply_id}]\n"
                f"<b>Niyet:</b> {analysis.summary}\n"
                f"<b>Oneri:</b> {analysis.suggested_action}\n\n"
                f"<b>Kimden:</b> {reply.from_name} &lt;{reply.from_email}&gt;\n"
                f"<b>Konu:</b> {reply.subject}\n"
            )
            if lead_name:
                notify += f"<b>İşletme:</b> {lead_name}\n"
            if sector or location:
                notify += f"<b>Kampanya:</b> {sector} — {location}\n"
            notify += f"\n<b>Mesaj:</b>\n{reply.body[:400]}"
            if len(reply.body) > 400:
                notify += "..."
            notify += f"\n\n<i>Yanitlamak icin:\nyanit {reply.reply_id} Merhaba, teklif icin...</i>"

            await bus.send(Message(
                sender=AgentName.INBOX_WATCHER,
                receiver=AgentName.SYSTEM,
                type=MessageType.USER_NOTIFY,
                content=notify,
            ))
            logger.info(f"Yanit bildirimi gonderildi: {reply.from_email} [{reply.reply_id}]")

        await asyncio.sleep(300)
