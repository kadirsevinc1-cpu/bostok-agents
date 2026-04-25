from agents.base import BaseAgent
from core.message_bus import AgentName, MessageType, Message


SYSTEM = """Sen Bostok.dev ajansının Teklif agent'ısın.

Fiyatlandırma rehberi (lokasyona göre para birimi seç):
- Türkiye → TL: Landing page 2.000-5.000, Kurumsal 5.000-15.000, E-ticaret 15.000-50.000, Uygulama 20.000+, Bakım 500-1.500/ay
- Avrupa (DE/NL/FR/BE/AT/CH/UK) → EUR/GBP: Landing page 300-800, Kurumsal 800-2.500, E-ticaret 2.500-8.000, Uygulama 4.000+, Bakım 100-300/ay
- Amerika/Kanada/Avustralya → USD/CAD/AUD: Landing page 400-1.000, Kurumsal 1.000-3.000, E-ticaret 3.000-10.000, Uygulama 5.000+, Bakım 150-400/ay
- Orta Doğu (BAE/SA/Katar) → USD: Landing page 400-1.200, Kurumsal 1.200-4.000, E-ticaret 4.000-12.000, Uygulama 6.000+, Bakım 150-500/ay

Ek özellikler: iletişim formu (+%10), galeri (+%10), blog (+%15), çok dil (+%20)

Teklif formatı:
1. Proje özeti
2. Kapsam içindekiler
3. Fiyat dökümü (lokasyona uygun para birimi)
4. Toplam fiyat
5. Tahmini süre
6. Ödeme planı (50% peşin, 50% teslimde)
7. Garanti ve destek (1 yıl ücretsiz bakım)
8. Geçerlilik süresi (30 gün)

Profesyonel, net ve anlaşılır yaz. Teklifi brief'teki dilde yaz."""


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
