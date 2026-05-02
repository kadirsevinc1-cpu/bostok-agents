import re
from pathlib import Path
from agents.base import BaseAgent
from core.message_bus import AgentName, MessageType, Message

OUTPUT_DIR = Path(__file__).parent.parent / "output" / "sites"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _cleanup_old_demos(demos_root: Path) -> None:
    import json
    import datetime as _dt
    today = _dt.date.today()
    for demo_dir in demos_root.iterdir():
        if not demo_dir.is_dir():
            continue
        meta_file = demo_dir / "meta.json"
        if not meta_file.exists():
            continue
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            expires = _dt.date.fromisoformat(meta.get("expires", ""))
            if today > expires:
                import shutil
                shutil.rmtree(demo_dir, ignore_errors=True)
        except Exception:
            pass


SYSTEM = """You are the Developer agent of Bostok.dev — a premium web design agency.

Your job: Build stunning websites that look like they cost $5,000+. No amateur work.

Tech stack: HTML5 + Tailwind CSS CDN + Google Fonts + Vanilla JS

NON-NEGOTIABLE quality standards:

STRUCTURE:
- Sticky nav with smooth scroll, mobile hamburger menu (JS toggle)
- Hero: full-viewport (min-h-screen), bold headline, subline, CTA button(s)
- Every nav link must have a matching section id — no broken anchors EVER
- Generous section padding: py-20 md:py-28
- Dark footer with links, social icons placeholder, copyright

VISUALS:
- Load a Google Font via <link> in <head> — never use default system fonts
- Rich color palette: avoid plain gray/white. Use gradients, dark backgrounds, or bold brand colors
- Hero background: CSS gradient mesh OR a real Unsplash image URL for the sector
  Format: https://images.unsplash.com/photo-XXXXXXXXXXXXX?w=1600&q=80
- Cards: rounded-2xl shadow-lg hover:-translate-y-1 transition-all duration-300
- Buttons: px-8 py-4 rounded-full font-semibold shadow-lg hover:shadow-xl transition
- Sections alternate: light bg → dark bg (or brand color bg) → light bg

JAVASCRIPT (inline at bottom):
- Mobile menu toggle
- Scroll-triggered fade-in: IntersectionObserver on sections
- Sticky nav: add shadow on scroll

CONTENT:
- NEVER leave {{PLACEHOLDER}} — fill every tag with realistic sector content
- NEVER use Lorem Ipsum
- Title: 50-60 chars | Meta description: 140-160 chars
- All image alt texts filled

Output: one self-contained index.html. Return HTML code only."""


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
        is_demo = msg.metadata.get("demo_build", False)

        if is_revision:
            await self._handle_revision(msg)
            return

        if is_demo:
            await self._handle_demo(msg)
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
            "Build a stunning, premium index.html. Every nav link must have a matching section id. "
            "Replace ALL {{PLACEHOLDER}} tags with real sector-specific content. "
            "Use Tailwind CSS CDN + Google Fonts. Return HTML code only."
        )

        # HTML kodunu çıkar
        html = self._extract_html(code)
        if not html:
            html = code

        # Placeholder tarayıcı — eğer {{...}} kaldıysa tekrar doldurtur
        html = await self._fill_placeholders(html, context=msg.content[:500])

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

    async def _handle_demo(self, msg: Message):
        import json
        import datetime as _dt
        from loguru import logger

        sector  = msg.metadata.get("sector", "demo")
        country = msg.metadata.get("country", "")
        concept = msg.content

        logger.info(f"Demo site yazılıyor: {sector} / {country}")

        demos_root = OUTPUT_DIR.parent / "demos"
        demos_root.mkdir(parents=True, exist_ok=True)

        # 1-year cleanup: remove demos older than 365 days
        _cleanup_old_demos(demos_root)

        # Sequential number from existing folders
        existing = sorted(
            [d for d in demos_root.iterdir() if d.is_dir() and d.name[0].isdigit()],
            key=lambda d: d.name,
        )
        num = len(existing) + 1

        slug = sector.lower().replace(" ", "_").replace("/", "_")
        country_slug = country.lower().replace(" ", "_")[:12]
        date_str = _dt.date.today().isoformat()
        folder_name = f"{num:03d}_{slug}_{country_slug}_{date_str}"
        demo_dir = demos_root / folder_name
        demo_dir.mkdir(parents=True, exist_ok=True)

        code = await self.ask(
            f"Website concept for a {sector} business ({country}):\n\n{concept}\n\n"
            "Build a world-class index.html from this concept. Requirements:\n"
            "- Full-viewport hero with gradient or Unsplash background image for this sector\n"
            "- Google Font loaded via <link> in <head>\n"
            "- Sticky nav, all nav links with matching section ids (no broken anchors)\n"
            "- Cards with rounded-2xl shadow-lg hover transitions\n"
            "- Scroll-triggered fade-in via IntersectionObserver (inline JS)\n"
            "- Dark footer with copyright\n"
            "- Fill ALL content with realistic {sector} business text — no placeholders\n"
            "- Title 50-60 chars, meta description 140-160 chars\n"
            "Return HTML code only."
        )

        html = self._extract_html(code)
        if not html:
            html = code

        html = await self._fill_placeholders(html, context=f"{sector} business in {country}")

        output_file = demo_dir / "index.html"
        output_file.write_text(html, encoding="utf-8")

        # Save meta.json alongside
        # Extract first meaningful line of concept as short summary
        summary_lines = [l.strip() for l in concept.splitlines() if l.strip() and not l.startswith("#")]
        summary = summary_lines[0][:120] if summary_lines else f"{sector} demo site"

        meta = {
            "num":     num,
            "sector":  sector,
            "country": country,
            "date":    date_str,
            "summary": summary,
            "folder":  folder_name,
            "lines":   len(html.splitlines()),
            "expires": (_dt.date.today() + _dt.timedelta(days=365)).isoformat(),
        }
        (demo_dir / "meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        logger.info(f"Demo site kaydedildi: {output_file}")
        self.save_observation(f"Demo #{num}: {sector} / {country}", importance=7.0)

        await self.send(
            AgentName.MANAGER, MessageType.RESULT,
            f"✅ <b>Demo site hazır!</b>\n"
            f"<b>#{num}</b> — {sector} / {country}\n"
            f"📁 <code>{folder_name}/</code>\n"
            f"📝 {summary[:80]}\n"
            f"📅 1 yıl saklanacak (son: {meta['expires']})",
            {"file_path": str(output_file), "project_name": folder_name},
        )

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

    async def _fill_placeholders(self, html: str, context: str = "", _attempt: int = 1) -> str:
        """If {{...}} placeholders remain, ask LLM to fill them. Max 2 attempts."""
        remaining = re.findall(r'\{\{[^}]+\}\}', html)
        if not remaining:
            return html
        if _attempt > 2:
            from loguru import logger
            logger.warning(f"Placeholder doldurulamadi, {len(remaining)} tanesini sildim: {remaining[:5]}")
            # Kalan placeholder'ları boş stringle temizle
            return re.sub(r'\{\{[^}]+\}\}', '', html)
        from loguru import logger
        logger.warning(f"Placeholder kaldı ({len(remaining)} adet, deneme {_attempt}/2): {remaining[:5]}")
        fixed = await self.ask(
            f"This HTML has unfilled placeholders: {', '.join(set(remaining))}\n"
            f"Context: {context}\n\n"
            f"Replace EVERY {'{{'} and {'}}'}  tag with realistic content. "
            "Do NOT leave any placeholder. Return the complete HTML. HTML code only."
            f"\n\nHTML:\n{html[:7000]}"
        )
        result = self._extract_html(fixed)
        filled = result if result else fixed
        return await self._fill_placeholders(filled, context, _attempt + 1)

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
