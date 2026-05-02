from pathlib import Path
from agents.base import BaseAgent
from core.message_bus import AgentName, MessageType, Message


SYSTEM = """You are the QA (Quality Control) agent of Bostok.dev agency.

Your job: Review the generated site code and produce a quality report.

CHECKLIST — evaluate each item:

STRUCTURE & SEMANTICS:
□ Semantic HTML5 elements used (header, nav, main, section, article, footer)
□ All nav links have matching section ids (no broken anchors)
□ Heading hierarchy correct (one h1, logical h2→h3 order)
□ No unclosed or malformed tags

VISUAL & DESIGN:
□ Google Font loaded via <link> in <head> (never system font fallback only)
□ Sections alternate backgrounds (not all same color)
□ Hero is full-viewport (min-h-screen) with real content — not generic
□ Cards have hover effects (transform / shadow transition)
□ Buttons have hover states and are visually distinct
□ Dark footer present with links and copyright

RESPONSIVE:
□ Meta viewport tag present
□ Mobile hamburger menu implemented and functional
□ No fixed-width elements that break on small screens
□ Padding/font sizes use responsive units (clamp, md: prefixes)

ACCESSIBILITY:
□ All images have descriptive alt text (not empty or "image")
□ ARIA labels on interactive elements (buttons, forms)
□ Color contrast adequate (text readable on backgrounds)
□ Form inputs have associated labels

SEO:
□ Title tag: 50–60 characters, sector-specific
□ Meta description: 140–160 characters
□ Open Graph tags (og:title, og:description, og:image)
□ Structured heading hierarchy supports SEO

CONTENT QUALITY:
□ Zero {{PLACEHOLDER}} tags remaining
□ Zero Lorem Ipsum text
□ Business name, sector, and location reflected in copy
□ CTA buttons have specific, action-oriented text (not just "Click Here")

PERFORMANCE:
□ No unnecessary external JS libraries loaded
□ IntersectionObserver scroll animations present
□ Images use Unsplash URLs with proper sizing (?w=1600&q=80)
□ No blocking scripts in <head>

Report format — group findings by category:
✅ PASS — item passes
⚠️ WARN — should fix, not blocking
❌ CRITICAL — must fix before publishing

End with:
📊 Overall score: X/10
🔧 Top 3 fixes needed (if any)"""


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
                f"Automated tool findings:\n{skill_summary}\n\n"
                "Write a detailed QA report based on these findings. "
                "Mark critical errors with ❌, warnings with ⚠️, passes with ✅. "
                "End with 📊 Overall score: X/10."
            )
        else:
            review_prompt = (
                f"Developer output:\n{msg.content}\n\n"
                "Run quality control and write a detailed report."
            )

        report = await self.ask(review_prompt)

        self.save_observation(f"QA raporu: {report[:150]}", importance=8.0)

        has_critical = "❌ CRITICAL" in report or (report.count("❌") >= 2)
        score = self._extract_score(report)
        top_fixes = self._extract_top_fixes(report)

        metadata = {
            "file_path": file_path,
            "site_dir": msg.metadata.get("site_dir", ""),
            "project_name": msg.metadata.get("project_name", ""),
            "has_critical_errors": has_critical,
            "score": score,
            "top_fixes": top_fixes,
        }
        await self.send(AgentName.MANAGER, MessageType.RESULT, report, metadata)

    @staticmethod
    def _extract_score(report: str) -> int:
        import re
        patterns = [
            r'[Oo]verall\s+score[:\s]+(\d+)\s*/\s*10',
            r'(\d+)\s*/\s*10',
            r'(\d+)\s+out\s+of\s+10',
            r'[Ss]core[:\s]+(\d+)',
        ]
        for pat in patterns:
            m = re.search(pat, report)
            if m:
                val = int(m.group(1))
                if 0 <= val <= 10:
                    return val
        return 0

    @staticmethod
    def _extract_top_fixes(report: str) -> list[str]:
        import re
        # LLM çeşitli başlıklar kullanabilir
        m = re.search(
            r'(?:Top \d+ fixes?|Fixes? needed|Önerilen düzeltmeler?)[^\n]*\n((?:[ \t]*[^\n]+\n?){1,8})',
            report, re.IGNORECASE,
        )
        if not m:
            # ❌ CRITICAL ile başlayan satırları topla
            fixes = re.findall(r'❌[^\n]+', report)
            return [f.strip() for f in fixes[:3]]
        lines = [l.strip() for l in m.group(1).splitlines() if l.strip()]
        return lines[:3]
