import asyncio
from agents.base import BaseAgent
from core.message_bus import AgentName, MessageType, Message

# Görsel çekmeyi haklı kılan sektörler (görsel ağırlıklı işler)
_VISUAL_SECTORS = {
    "restoran", "restaurant", "kafe", "cafe", "pastane", "bakery",
    "otel", "hotel", "guzellik_salonu", "beauty salon", "berber", "barbershop",
    "emlak", "real estate", "spor_salonu", "gym", "fitness",
    "turizm", "tourism", "fotograf", "photographer",
}

# Brief'te görsel talep eden anahtar kelimeler
_VISUAL_KEYWORDS = [
    "görsel", "fotoğraf", "resim", "galeri", "image", "photo", "gallery",
    "video", "görünüm", "estetik", "tasarım ağırlıklı", "showcase",
]


def _should_fetch_images(brief: str, sector: str) -> bool:
    """Brief ve sektöre göre görsel çekme gerekip gerekmediğine karar ver."""
    # Açıkça "görsel istemiyorum" denmişse hayır
    if any(w in brief.lower() for w in ["görsel yok", "görsel istemiyorum", "no image", "no photo"]):
        return False
    # Görsel ağırlıklı sektörse evet
    if sector.lower() in _VISUAL_SECTORS:
        return True
    # Brief'te görsel kelimesi geçiyorsa evet
    if any(w in brief.lower() for w in _VISUAL_KEYWORDS):
        return True
    # Teknik/hukuki/muhasebe gibi sektörler için hayır (metin ağırlıklı)
    text_heavy = ["avukat", "law", "muhasebe", "accounting", "yazılım", "software", "it ", "sigorta"]
    if any(w in (sector + " " + brief).lower() for w in text_heavy):
        return False
    # Varsayılan: evet (çoğu site görsel kullanır)
    return True


SYSTEM = """You are the Designer agent of Bostok.dev agency.

Your job: Create a detailed design guide and HTML/CSS skeleton for the client's site.

Design guide must include:
1. Color palette (HEX codes)
2. Typography (font family, sizes)
3. Layout structure (header, hero, sections, footer)
4. Component list (nav, cards, buttons)
5. Mobile responsiveness notes
6. Animation suggestions

Also: Write a basic HTML/CSS skeleton (with content placeholders).
Modern, responsive design. Use Tailwind CSS."""


class DesignerAgent(BaseAgent):
    name = AgentName.DESIGNER
    system_prompt = SYSTEM
    max_tokens = 3000

    async def loop(self):
        msg = await self.receive(timeout=1.0)
        if not msg:
            return
        await self._handle(msg)

    async def _handle(self, msg: Message):
        from loguru import logger
        from core.skills.design_kb import format_design_hint
        from core.skills.web_inspiration import get_inspiration
        from core.skills.image_generator import get_best_images

        logger.info(f"Tasarım hazırlanıyor: {msg.content[:60]}")

        sector   = msg.metadata.get("sector", "") or msg.content.split()[0]
        location = msg.metadata.get("location", "")

        design_hint = format_design_hint(msg.content)
        needs_images = _should_fetch_images(msg.content, sector)

        if needs_images:
            # confirmed=True ise müşteri onaylı proje → tam görsel seti
            confirmed = msg.metadata.get("confirmed", False)
            img_mode  = "full" if confirmed else "demo"
            inspiration, images = await asyncio.gather(
                get_inspiration(sector, location),
                get_best_images(sector, project_name=msg.metadata.get("project_name", ""), mode=img_mode),
            )
            image_hint = ""
            if images and images.hero_url:
                image_hint = (
                    f"\n[Görseller — {images.source}]\n"
                    f"Hero: {images.hero_url}\n"
                    f"Hizmet: {images.service_url}\n"
                    f"Arka plan: {images.bg_url}\n"
                )
            logger.info(f"Görsel çekildi: {images.source if images else '-'}")
        else:
            inspiration = await get_inspiration(sector, location)
            images = None
            image_hint = ""
            logger.info("Görsel atlandı (sektör/brief'e göre gerekli değil)")

        design = await self.ask(
            f"Proje içerikleri ve brief:\n{msg.content}\n\n"
            f"{design_hint}\n\n"
            f"{inspiration.format_for_designer()}\n"
            f"{image_hint}"
            "Bu proje için:\n"
            "1. Yukarıdaki tasarım rehberi ve ilham verilerine uygun detaylı tasarım kararları yaz\n"
            "2. Tailwind CSS kullanarak HTML iskeleti oluştur"
            + (" — sağlanan görsel URL'lerini kullan\n" if image_hint else "\n")
            + "3. Renk paleti ve font seçimlerini kısa gerekçelendir"
        )

        self.save_observation(f"Tasarım: {design[:150]}", importance=7.5)
        meta = {"images": {"hero": images.hero_url, "service": images.service_url}} if images else {}
        await self.send(AgentName.MANAGER, MessageType.RESULT, design, meta)
