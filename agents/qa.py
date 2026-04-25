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
        from core.skills.html_validator import validate_html
        from core.skills.link_checker import check_links
        from core.skills.seo_checker import check_seo

        logger.info(f"QA kontrolü başladı: {msg.content[:60]}")

        file_path = msg.metadata.get("file_path", "")
        html_content = ""
        if file_path and Path(file_path).exists():
            html_content = Path(file_path).read_text(encoding="utf-8")

        if html_content:
            # Skill tabanlı analiz — 0 token, LLM'e özet gönderilir
            html_rep  = validate_html(html_content)
            link_rep  = check_links(html_content)
            seo_rep   = check_seo(html_content)

            skill_summary = (
                f"=== Otomatik Analiz ===\n"
                f"HTML Yapısı:\n{html_rep.summary()}\n\n"
                f"Linkler:\n{link_rep.summary()}\n\n"
                f"SEO:\n{seo_rep.summary()}"
            )
            logger.info(f"QA skill analizi tamamlandı — SEO: {seo_rep.score}/100, "
                        f"HTML hataları: {len(html_rep.errors)}")

            review_prompt = (
                f"Otomatik araçların tespitleri:\n{skill_summary}\n\n"
                "Bu bulgulara dayanarak detaylı QA raporu yaz. "
                "Kritik hataları ❌, uyarıları ⚠️, geçenleri ✅ ile işaretle. "
                "Sona 📊 Genel puan: X/10 ekle."
            )
        else:
            review_prompt = (
                f"Geliştirici çıktısı:\n{msg.content}\n\n"
                "Kalite kontrolden geçir ve detaylı rapor yaz."
            )

        report = await self.ask(review_prompt)

        self.save_observation(f"QA raporu: {report[:150]}", importance=8.0)

        has_critical = "❌" in report
        metadata = {
            "file_path": file_path,
            "site_dir": msg.metadata.get("site_dir", ""),
            "project_name": msg.metadata.get("project_name", ""),
            "has_critical_errors": has_critical,
        }
        await self.send(AgentName.MANAGER, MessageType.RESULT, report, metadata)
