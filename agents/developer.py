import re
from pathlib import Path
from agents.base import BaseAgent
from core.message_bus import AgentName, MessageType, Message

OUTPUT_DIR = Path(__file__).parent.parent / "output" / "sites"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


SYSTEM = """Sen Bostok.dev ajansının Developer agent'ısın.

Görevin: Tasarım rehberine ve içeriklere göre tam çalışan web sitesi kodu yazmak.

Teknoloji:
- HTML5 + Tailwind CSS (CDN)
- Vanilla JavaScript (gerekirse)
- Responsive (mobile-first)
- SEO meta tagları
- Hızlı yüklenen, temiz kod

Her proje için tek bir index.html dosyası üret (all-in-one).
İçerik placeholder kullanma — gerçek içerikleri yerleştir.
Kod çalışır durumda olmalı, tarayıcıda açılabilmeli."""


class DeveloperAgent(BaseAgent):
    name = AgentName.DEVELOPER
    system_prompt = SYSTEM
    max_tokens = 4000

    async def loop(self):
        msg = await self.receive(timeout=1.0)
        if not msg:
            return
        await self._handle(msg)

    async def _handle(self, msg: Message):
        from loguru import logger
        from core import memory
        from core.knowledge import get_template, detect_template, log_error

        logger.info(f"Kod yazılıyor: {msg.content[:60]}")

        # Uygun şablonu seç ve yükle
        template_name = detect_template(msg.content)
        template = get_template(template_name)
        template_hint = f"\n\nŞablon ({template_name}):\n{template[:2000]}" if template else ""

        code = await self.ask(
            f"Tasarım ve içerik:\n{msg.content}{template_hint}\n\n"
            "Şablonu referans alarak tam çalışan index.html yaz. "
            "Tüm {{PLACEHOLDER}}'ları gerçek içerikle doldur. "
            "Tailwind CSS CDN kullan. Sadece HTML kodu döndür."
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
