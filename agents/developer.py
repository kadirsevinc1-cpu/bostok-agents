import re
from pathlib import Path
from agents.base import BaseAgent
from core.message_bus import AgentName, MessageType, Message

OUTPUT_DIR = Path(__file__).parent.parent / "output" / "sites"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


SYSTEM = """You are the Developer agent of Bostok.dev agency.

Your job: Write fully working website code based on the design guide and content.

Tech stack:
- HTML5 + Tailwind CSS (CDN)
- Vanilla JavaScript (if needed)
- Responsive (mobile-first)
- SEO meta tags
- Fast-loading, clean code

Output a single index.html file per project (all-in-one).
Never use content placeholders — fill in real content.
Code must be functional and openable in a browser."""


class DeveloperAgent(BaseAgent):
    name = AgentName.DEVELOPER
    system_prompt = SYSTEM
    max_tokens = 8000

    async def loop(self):
        msg = await self.receive(timeout=1.0)
        if not msg:
            return
        await self._handle(msg)

    async def _handle(self, msg: Message):
        from loguru import logger
        from core import memory

        is_revision = msg.metadata.get("revision", False)

        if is_revision:
            await self._handle_revision(msg)
            return

        from core.knowledge import get_template, detect_template, log_error
        from core.skills.video_finder import find_video, get_css_fallback_animation

        logger.info(f"Kod yazılıyor: {msg.content[:60]}")

        sector = msg.metadata.get("sector", "") or ""

        # Şablonu seç
        template_name = detect_template(msg.content)
        template = get_template(template_name)
        template_hint = f"\n\nTemplate ({template_name}):\n{template[:2000]}" if template else ""

        video_hint = ""
        if sector:
            video = await find_video(sector)
            if video.found:
                video_hint = (
                    f"\n\n[Background Video — Pexels]\n"
                    f"Use in hero section:\n{video.html_snippet}\n"
                    f"(Add dark overlay + white text on top of video)"
                )
                logger.info(f"Video bulundu ve HTML'e ekleniyor: {sector}")
            else:
                css_anim = get_css_fallback_animation(sector)
                video_hint = f"\n\n[Hero Background — CSS Animation]\n{css_anim}"

        code = await self.ask(
            f"Design and content:\n{msg.content}{template_hint}{video_hint}\n\n"
            "Using the template as reference, write a fully working index.html. "
            "Replace all {{PLACEHOLDER}} tags with real content. "
            "Use Tailwind CSS CDN. Return HTML code only."
        )

        # HTML kodunu çıkar
        html = self._extract_html(code)
        if not html:
            html = code

        # Dosyaya kaydet
        project_name = msg.metadata.get("project_name", f"site_{len(list(OUTPUT_DIR.iterdir()))}")
        site_dir = OUTPUT_DIR / project_name
        site_dir.mkdir(exist_ok=True)
        output_file = site_dir / "index.html"
        output_file.write_text(html, encoding="utf-8")

        logger.info(f"Site kaydedildi: {output_file}")
        memory.add_task(f"Site kodu yazıldı: {project_name}", f"Dosya: {output_file}", "Developer")

        self.save_observation(f"Site yazıldı: {output_file}", importance=8.5)
        result = f"✅ Kod yazıldı!\nDosya: {output_file}\nSatır sayısı: {len(html.splitlines())}"
        await self.send(AgentName.MANAGER, MessageType.RESULT, result,
                       {"file_path": str(output_file), "project_name": project_name})

    async def _handle_revision(self, msg: Message):
        from loguru import logger
        from core import memory

        revision = msg.content
        site_dir = msg.metadata.get("site_dir", "")
        project_name = msg.metadata.get("project_name", "site")
        logger.info(f"Revize uygulanıyor [{project_name}]: {revision[:60]}")

        site_path = Path(site_dir) / "index.html" if site_dir else None
        existing_html = ""
        if site_path and site_path.exists():
            existing_html = site_path.read_text(encoding="utf-8")
        else:
            logger.warning(f"Revize: mevcut dosya bulunamadı — {site_dir}")
            await self.send(AgentName.MANAGER, MessageType.RESULT,
                            "❌ Revize için mevcut site dosyası bulunamadı.",
                            {"file_path": "", "project_name": project_name})
            return

        code = await self.ask(
            f"Apply the following revision to the HTML site below:\n\n"
            f"REVISION REQUEST: {revision}\n\n"
            f"CURRENT HTML ({len(existing_html)} chars):\n{existing_html[:6000]}\n\n"
            "Apply the change and return the complete HTML file. Return HTML code only."
        )

        html = self._extract_html(code)
        if not html:
            html = code

        site_path.write_text(html, encoding="utf-8")
        logger.info(f"Revize kaydedildi: {site_path}")
        memory.add_task(f"Revize: {revision[:80]}", f"Dosya: {site_path}", "Developer")
        self.save_observation(f"Revize uygulandı: {revision[:100]}", importance=8.0)

        result = f"✅ Revize uygulandı!\nDosya: {site_path}\nDeğişiklik: {revision[:100]}"
        await self.send(AgentName.MANAGER, MessageType.RESULT, result,
                       {"file_path": str(site_path), "project_name": project_name})

    def _extract_html(self, text: str) -> str:
        # ```html ... ``` bloğunu çıkar
        match = re.search(r'```html\s*(.*?)```', text, re.DOTALL)
        if match:
            return match.group(1).strip()
        match = re.search(r'```\s*(<!DOCTYPE.*?)```', text, re.DOTALL)
        if match:
            return match.group(1).strip()
        if "<!DOCTYPE" in text or "<html" in text:
            return text
        return ""
