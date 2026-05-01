"""LinkedInAgent — finds decision maker profiles and generates connection messages."""
from loguru import logger
from agents.base import BaseAgent
from core.message_bus import AgentName, MessageType, Message

SYSTEM = """You are the LinkedIn outreach specialist of Bostok.dev.
You find business owners and decision makers on LinkedIn and craft personalized connection requests.
Keep messages under 300 characters, genuine, non-salesy."""


class LinkedInAgent(BaseAgent):
    name = AgentName.LINKEDIN
    system_prompt = SYSTEM
    max_tokens = 400

    async def loop(self):
        msg = await self.receive(timeout=1.0)
        if not msg:
            return
        await self._handle(msg)

    async def _handle(self, msg: Message):
        metadata = msg.metadata or {}
        sector   = metadata.get("sector", "")
        location = metadata.get("location", "")
        lang     = metadata.get("languages", ["en"])[0]

        if not sector or not location:
            return

        logger.info(f"LinkedIn: {sector}/{location}")

        try:
            from integrations.linkedin_finder import find_and_notify
            results = await find_and_notify(sector, location, lang=lang, max_leads=5)
        except Exception as e:
            logger.error(f"LinkedIn agent error: {e}")
            await self.send(AgentName.MANAGER, MessageType.RESULT,
                            f"LinkedIn error: {e}")
            return

        if not results:
            await self.send(AgentName.MANAGER, MessageType.RESULT,
                            f"LinkedIn: No profiles found for {sector}/{location}")
            return

        # Build Telegram notification with clickable profiles + ready-to-send messages
        notify_lines = [f"🔗 <b>LinkedIn Leads — {sector} / {location}</b>\n"]
        for r in results:
            notify_lines.append(
                f"👤 <b>{r['name']}</b> — {r['title']}"
                f"{' @ ' + r['company'] if r['company'] else ''}\n"
                f"🔗 {r['profile_url']}\n"
                f"📝 <i>{r['message']}</i>\n"
            )
        notify_lines.append("─────\nConnect manually on LinkedIn and paste the message above.")

        await self.send(AgentName.SYSTEM, MessageType.USER_NOTIFY,
                        "\n".join(notify_lines))
        await self.send(AgentName.MANAGER, MessageType.RESULT,
                        f"LinkedIn: {len(results)} profil bulundu — {sector}/{location}")
