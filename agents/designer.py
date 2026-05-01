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


SYSTEM = """You are the Designer agent of Bostok.dev — a premium web design agency.

Your job: Create a bold, conversion-focused design guide for the client's website.
Generic is the enemy. Every decision must be specific to the sector and brand.

Design guide must include:

1. VISUAL STYLE — choose one and commit fully:
   Minimalist Luxury | Bold & Energetic | Warm & Approachable | Dark Premium | Corporate Trust

2. COLOR PALETTE — specific HEX codes, not generic blues or grays:
   - Primary brand color (bold, distinctive)
   - Secondary / accent
   - Background (can be dark, cream, off-white — not plain white)
   - Text / heading color
   Justify each choice with the emotion/association it creates.

3. TYPOGRAPHY — specific Google Font pair:
   - Heading font + exact sizes (h1: 56px, h2: 36px, h3: 24px)
   - Body font + size (16px) + line-height
   Choose fonts that feel premium — not just "Roboto" or "Open Sans"

4. HERO SECTION — be specific:
   - Full viewport? Split layout? Video background? Gradient mesh?
   - Exact headline structure (bold claim + supporting line)
   - CTA button copy and style
   - Any background treatment (overlay, pattern, image)

5. LAYOUT & SECTIONS — use the blueprint for the site type, then adapt:

   SECTION BLUEPRINTS (follow this order):
   • SaaS / App:      Hero → Features → How It Works → Pricing → Testimonials → CTA → Footer
   • Restaurant/Cafe: Hero → Menu Highlights → Gallery → About → Reservations → Location → Footer
   • Service/Local:   Hero → Services → Why Us → Team → Testimonials → Contact → Footer
   • Portfolio:       Hero → About → Projects → Skills → Process → Contact → Footer
   • E-commerce:      Hero → Featured Products → Categories → Benefits → Reviews → Newsletter → Footer
   • Medical/Clinic:  Hero → Services → Team → Process → FAQ → Appointment → Footer
   • Hotel/Tourism:   Hero → Rooms/Tours → Gallery → Amenities → Testimonials → Booking → Footer
   • Real Estate:     Hero → Featured Listings → Services → About → Testimonials → Contact → Footer

   Every section must have a unique id matching a nav link. Never skip a section — adapt content instead.

6. COMPONENTS — exact specs:
   - Nav: sticky/transparent? logo left or center? CTA button in nav?
   - Cards: border-radius, shadow depth, hover effect
   - Buttons: rounded-full or square? gradient or solid? hover animation

7. MICRO-ANIMATIONS:
   - Scroll-triggered fade-ins
   - Hover effects on cards/buttons
   - Any parallax or count-up numbers

Provide an HTML skeleton using Tailwind CSS that demonstrates the design.
Use real section ids that match navigation links (no broken anchors)."""


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
            f"Project content and brief:\n{msg.content}\n\n"
            f"{design_hint}\n\n"
            f"{inspiration.format_for_designer()}\n"
            f"{image_hint}"
            "For this project:\n"
            "1. Write detailed design decisions based on the design guide and inspiration above\n"
            "2. Build an HTML skeleton using Tailwind CSS"
            + (" — use the provided image URLs\n" if image_hint else "\n")
            + "3. Briefly justify the color palette and font choices"
        )

        self.save_observation(f"Tasarım: {design[:150]}", importance=7.5)
        meta = {"images": {"hero": images.hero_url, "service": images.service_url}} if images else {}
        await self.send(AgentName.MANAGER, MessageType.RESULT, design, meta)
