from agents.base import BaseAgent
from core.message_bus import AgentName, MessageType, Message


SYSTEM = """Sen Bostok.dev ajansının İçerik Yazarı agent'ısın.

Görevin: Müşteri sitesi için profesyonel web içerikleri yazmak.

Yazacakların:
- Ana sayfa metni (hero, hizmetler, hakkında özeti, CTA)
- Hakkımızda sayfası
- Hizmetler sayfası
- İletişim sayfası metni
- SEO meta açıklamaları

Kurallar:
- Müşterinin sektörüne uygun dil kullan
- SEO dostu yaz (anahtar kelimeler doğal aksa)
- Türkçe yaz, gerekirse İngilizce de ekle
- Samimi ve profesyonel ton
- Her bölüm için başlık + içerik formatı kullan
- CTA (harekete geçirici çağrı) ekle her sayfaya"""


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
        logger.info(f"İçerik yazılıyor: {msg.content[:60]}")

        content = await self.ask(
            f"Proje brief'i:\n{msg.content}\n\n"
            "Bu proje için tüm sayfa içeriklerini yaz. "
            "Her sayfa için başlık ve içerik bölümlerini net ayır."
        )

        self.save_observation(f"İçerik yazıldı: {content[:150]}", importance=7.0)
        await self.send(AgentName.MANAGER, MessageType.RESULT, content)
