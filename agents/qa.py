from pathlib import Path
from agents.base import BaseAgent
from core.message_bus import AgentName, MessageType, Message


SYSTEM = """Sen Bostok.dev ajansının QA (Kalite Kontrol) agent'ısın.

Görevin: Yazılan site kodunu inceleyip kalite raporu çıkarmak.

Kontrol listesi:
1. HTML geçerliliği (tag kapatma, yapı)
2. Tailwind CSS doğru kullanımı
3. Responsive tasarım (mobile uyumluluk)
4. SEO meta tagları (title, description, og:)
5. Erişilebilirlik (alt text, aria label)
6. Performans (gereksiz script, büyük inline style)
7. İçerik eksiksizliği (placeholder kalmış mı?)
8. İletişim formu çalışır mı?
9. Bağlantılar doğru mu?
10. Genel görünüm ve profesyonellik

Rapor formatı:
✅ Geçen kontroller
⚠️ Uyarılar (düzeltilmeli ama kritik değil)
❌ Kritik hatalar (yayına almadan önce düzeltilmeli)
📊 Genel puan: X/10"""


class QAAgent(BaseAgent):
    name = AgentName.QA
    system_prompt = SYSTEM
    max_tokens = 1500

    async def loop(self):
        msg = await self.receive(timeout=1.0)
        if not msg:
            return
        await self._handle(msg)

    async def _handle(self, msg: Message):
        from loguru import logger
        logger.info(f"QA kontrolü başladı: {msg.content[:60]}")

        # Dosyayı oku
        file_path = msg.metadata.get("file_path", "")
        html_content = ""
        if file_path and Path(file_path).exists():
            html_content = Path(file_path).read_text(encoding="utf-8")

        review_content = html_content if html_content else msg.content

        report = await self.ask(
            f"Aşağıdaki web sitesi kodunu kalite kontrolden geçir:\n\n{review_content[:3000]}\n\n"
            "Kontrol listesindeki tüm maddeleri incele ve detaylı rapor yaz."
        )

        self.save_observation(f"QA raporu: {report[:150]}", importance=8.0)

        # Kritik hata var mı kontrol et
        has_critical = "❌" in report
        metadata = {"file_path": file_path, "has_critical_errors": has_critical}

        if has_critical:
            await self.send(AgentName.MANAGER, MessageType.STATUS,
                           f"⚠️ QA kritik hata buldu:\n{report}", metadata)
        else:
            await self.send(AgentName.MANAGER, MessageType.RESULT, report, metadata)
