from agents.base import BaseAgent
from core.message_bus import AgentName, MessageType, Message


SYSTEM = """Sen Bostok.dev ajansının Analist agent'ısın.

Görevin: Müşteri taleplerini analiz edip net bir proje brief'i çıkarmak.

Brief formatı:
1. Proje Adı
2. Müşteri Sektörü
3. Hedef Kitle
4. İstenen Sayfalar (Ana sayfa, Hakkımızda, vb.)
5. Özellikler (iletişim formu, galeri, vb.)
6. Renk/Stil tercihi
7. Referans siteler (varsa)
8. Tahmini süre
9. Özel notlar

Eğer müşteri bilgisi eksikse makul varsayımlar yap ve belirt."""


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
        logger.info(f"Analist brief hazırlıyor: {msg.content[:60]}")

        brief = await self.ask(
            f"Müşteri talebi:\n{msg.content}\n\nBu talep için detaylı proje brief'i hazırla."
        )

        import re, uuid
        name_match = re.search(r'Proje Ad[ıi]\s*[:\-]\s*(.+)', brief)
        project_name = name_match.group(1).strip()[:40] if name_match else uuid.uuid4().hex[:8]
        project_name = re.sub(r'[^\w\-]', '_', project_name)

        self.save_observation(f"Brief: {brief[:200]}", importance=8.0)
        await self.send(AgentName.MANAGER, MessageType.RESULT, brief,
                        {"project_name": project_name})
