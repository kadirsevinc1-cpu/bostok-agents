from agents.base import BaseAgent
from core.message_bus import AgentName, MessageType, Message


SYSTEM = """Sen Bostok.dev ajansının Tasarım agent'ısın.

Görevin: Müşteri sitesi için detaylı tasarım rehberi ve HTML/CSS iskelet oluşturmak.

Tasarım rehberi içermeli:
1. Renk paleti (HEX kodları)
2. Tipografi (font ailesi, boyutlar)
3. Layout yapısı (header, hero, sections, footer)
4. Komponent listesi (nav, kartlar, butonlar)
5. Mobil uyumluluk notları
6. Animasyon önerileri

Ayrıca: Temel HTML/CSS iskeleti yaz (içerik placeholder'larıyla).
Modern, responsive tasarım. Tailwind CSS kullan."""


class DesignerAgent(BaseAgent):
    name = AgentName.DESIGNER
    system_prompt = SYSTEM
    max_tokens = 3000

    async def loop(self):
        msg = await self.receive(timeout=1.0)
        if not msg:
            return
        await self._handle(msg)

    async def _handle(self, msg: Message):
        from loguru import logger
        from core.skills.design_kb import format_design_hint
        logger.info(f"Tasarım hazırlanıyor: {msg.content[:60]}")

        design_hint = format_design_hint(msg.content)

        design = await self.ask(
            f"Proje içerikleri ve brief:\n{msg.content}\n\n"
            f"{design_hint}\n"
            "Bu proje için:\n"
            "1. Yukarıdaki tasarım rehberine uygun detaylı tasarım kararları yaz\n"
            "2. Tailwind CSS kullanarak HTML iskeleti oluştur\n"
            "3. Renk paleti ve font seçimlerini kısa gerekçelendir"
        )

        self.save_observation(f"Tasarım: {design[:150]}", importance=7.5)
        await self.send(AgentName.MANAGER, MessageType.RESULT, design)
