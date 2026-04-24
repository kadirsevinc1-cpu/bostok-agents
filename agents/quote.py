from agents.base import BaseAgent
from core.message_bus import AgentName, MessageType, Message


SYSTEM = """Sen Bostok.dev ajansının Teklif agent'ısın.

Fiyatlandırma rehberi:
- Landing page (1 sayfa): 2.000 - 5.000 TL
- Kurumsal site (5 sayfa): 5.000 - 15.000 TL
- E-ticaret sitesi: 15.000 - 50.000 TL
- Özel web uygulaması: 20.000 TL+
- Ek özellikler: iletişim formu (+500), galeri (+500), blog (+1.000), çok dil (+2.000)
- Bakım paketi: 500-1.500 TL/ay

Teklif formatı:
1. Proje özeti
2. Kapsam içindekiler (neleri yapacağız)
3. Fiyat dökümü
4. Toplam fiyat
5. Tahmini süre
6. Ödeme planı (50% peşin, 50% teslimde önerilir)
7. Garanti ve destek
8. Geçerlilik süresi (30 gün)

Profesyonel, net ve anlaşılır yaz."""


class QuoteAgent(BaseAgent):
    name = AgentName.QUOTE
    system_prompt = SYSTEM
    max_tokens = 1500

    async def loop(self):
        msg = await self.receive(timeout=1.0)
        if not msg:
            return
        await self._handle(msg)

    async def _handle(self, msg: Message):
        from loguru import logger
        logger.info(f"Teklif hazırlanıyor: {msg.content[:60]}")

        quote = await self.ask(
            f"Proje brief'i:\n{msg.content}\n\nBu proje için detaylı teklif hazırla."
        )

        self.save_observation(f"Teklif: {quote[:200]}", importance=8.5)
        await self.send(AgentName.MANAGER, MessageType.RESULT, quote)
