from agents.base import BaseAgent
from core.message_bus import AgentName, MessageType, Message


SYSTEM = """You are the Content Writer agent of Bostok.dev agency.

Your job: Write professional web content for the client's site.

You will write:
- Homepage copy (hero, services, about summary, CTA)
- About page
- Services page
- Contact page copy
- SEO meta descriptions

Rules:
- Determine content language from client's location:
  Turkey → Turkish | Germany/Austria/Switzerland → German | UK/USA/Canada/Australia/UAE → English | France → French | Netherlands/Belgium → English
- Use sector-appropriate terminology
- Write SEO-friendly (keywords flow naturally)
- Tone: genuine and professional
- Use heading + content format for each section
- Add a CTA on every page
- Zero spelling or grammar errors"""


class ContentAgent(BaseAgent):
    name = AgentName.CONTENT
    system_prompt = SYSTEM
    max_tokens = 2000

    async def loop(self):
        msg = await self.receive(timeout=1.0)
        if not msg:
            return
        await self._handle(msg)

    async def _handle(self, msg: Message):
        from loguru import logger
        from core.skills.sector_kb import detect_sector, get_sector_context
        logger.info(f"İçerik yazılıyor: {msg.content[:60]}")

        sector = detect_sector(msg.content)
        kb_ctx = get_sector_context(sector)

        content = await self.ask(
            f"Project brief:\n{msg.content}\n\n"
            + (f"{kb_ctx}\n\n" if kb_ctx else "")
            + "Write all page content for this project.\n"
            "Requirements:\n"
            "1. Clear headings and sections for each page (Home, About, Services, Contact)\n"
            "2. Each page section: 1 H1 or H2 heading + 2-3 sentences + CTA\n"
            "3. At the end, add a section called '=== SEO KEYWORDS ===' with:\n"
            "   - Primary keyword (1-2 words, highest search intent)\n"
            "   - Secondary keywords (3-5 phrases, long-tail)\n"
            "   - Meta title (50-60 chars)\n"
            "   - Meta description (140-160 chars)\n"
            "   - Suggested URL slug\n"
            "All keywords must be in the same language as the content."
        )

        self.save_observation(f"İçerik yazıldı: {content[:150]}", importance=7.0)
        await self.send(AgentName.MANAGER, MessageType.RESULT, content,
                        {"sector": sector})
