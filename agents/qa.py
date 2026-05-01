from pathlib import Path
from agents.base import BaseAgent
from core.message_bus import AgentName, MessageType, Message


SYSTEM = """You are the QA (Quality Control) agent of Bostok.dev agency.

Your job: Review the generated site code and produce a quality report.

Checklist:
1. HTML validity (tag closing, structure)
2. Tailwind CSS correct usage
3. Responsive design (mobile compatibility)
4. SEO meta tags (title, description, og:)
5. Accessibility (alt text, aria labels)
6. Performance (unnecessary scripts, large inline styles)
7. Content completeness (any placeholders left?)
8. Contact form working?
9. Links correct?
10. Overall appearance and professionalism

Report format:
✅ Passed checks
⚠️ Warnings (should fix but not critical)
❌ Critical errors (must fix before publishing)
📊 Overall score: X/10"""


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
        from core.skills.accessibility_checker import check_accessibility
        from core.skills.security_checker import check_security

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
            a11y_rep  = check_accessibility(html_content)
            sec_rep   = check_security(html_content)

            skill_summary = (
                f"=== Otomatik Analiz ===\n"
                f"HTML Yapısı:\n{html_rep.summary()}\n\n"
                f"Linkler:\n{link_rep.summary()}\n\n"
                f"SEO:\n{seo_rep.summary()}\n\n"
                f"Erişilebilirlik:\n{a11y_rep.summary()}\n\n"
                f"Güvenlik:\n{sec_rep.summary()}"
            )
            logger.info(
                f"QA skill analizi tamamlandi — SEO: {seo_rep.score}/100, "
                f"HTML hatalari: {len(html_rep.errors)}, "
                f"A11y hatalari: {len(a11y_rep.errors)}, "
                f"Guvenlik skoru: {sec_rep.score}/100"
            )

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
