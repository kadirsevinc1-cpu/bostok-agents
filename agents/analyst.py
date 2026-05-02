from agents.base import BaseAgent
from core.message_bus import AgentName, MessageType, Message


SYSTEM = """You are the Analyst agent of Bostok.dev agency.

Your job: Analyze client requests and produce a clear project brief.

Brief format:
1. Project Name
2. Client Sector
3. Target Audience
4. Requested Pages (Home, About, etc.)
5. Features (contact form, gallery, etc.)
6. Color/Style preference
7. Reference sites (if any)
8. Estimated timeline
9. Special notes

If client information is missing, make reasonable assumptions and state them."""


class AnalystAgent(BaseAgent):
    name = AgentName.ANALYST
    system_prompt = SYSTEM
    max_tokens = 1200

    async def loop(self):
        msg = await self.receive(timeout=1.0)
        if not msg:
            return
        await self._handle(msg)

    async def _handle(self, msg: Message):
        from loguru import logger
        from core.skills.sector_kb import detect_sector, get_sector_context
        logger.info(f"Analist brief hazırlıyor: {msg.content[:60]}")

        sector = detect_sector(msg.content)
        kb_ctx = get_sector_context(sector)

        brief = await self.ask(
            f"Client request:\n{msg.content}\n\n"
            + (f"{kb_ctx}\n\n" if kb_ctx else "")
            + "Prepare a detailed project brief for this request."
        )

        import re, uuid, unicodedata
        name_match = re.search(r'Proje Ad[ıi]\s*[:\-]\s*(.+)', brief, re.IGNORECASE)
        raw_name = name_match.group(1).strip()[:40] if name_match else ""
        # Unicode → ASCII (ş→s, ğ→g, ü→u ...) sonra dosya-güvenli slug
        nfkd = unicodedata.normalize("NFKD", raw_name)
        ascii_name = nfkd.encode("ascii", "ignore").decode("ascii")
        project_name = re.sub(r'[^a-zA-Z0-9\-]', '_', ascii_name).strip('_') or uuid.uuid4().hex[:8]

        self.save_observation(f"Brief: {brief[:200]}", importance=8.0)
        await self.send(AgentName.MANAGER, MessageType.RESULT, brief,
                        {"project_name": project_name})
