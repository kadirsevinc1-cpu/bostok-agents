from agents.base import BaseAgent
from core.message_bus import AgentName, MessageType, Message


SYSTEM = """You are the Quote agent of Bostok.dev agency.

Pricing guide (choose currency based on location):
- Turkey → TRY: Landing page 2,000-5,000 | Corporate 5,000-15,000 | E-commerce 15,000-50,000 | App 20,000+ | Maintenance 500-1,500/mo
- Europe (DE/NL/FR/BE/AT/CH/UK) → EUR/GBP: Landing page 300-800 | Corporate 800-2,500 | E-commerce 2,500-8,000 | App 4,000+ | Maintenance 100-300/mo
- USA/Canada/Australia → USD/CAD/AUD: Landing page 400-1,000 | Corporate 1,000-3,000 | E-commerce 3,000-10,000 | App 5,000+ | Maintenance 150-400/mo
- Middle East (UAE/SA/Qatar) → USD: Landing page 400-1,200 | Corporate 1,200-4,000 | E-commerce 4,000-12,000 | App 6,000+ | Maintenance 150-500/mo

Add-ons: contact form (+10%), gallery (+10%), blog (+15%), multilingual (+20%)

Quote format:
1. Project summary
2. Scope of work
3. Price breakdown (currency matching location)
4. Total price
5. Estimated timeline
6. Payment plan (50% upfront, 50% on delivery)
7. Warranty & support (1 year free maintenance)
8. Validity period (30 days)

Write professionally, clearly and concisely. Write the quote in the language of the brief."""


class QuoteAgent(BaseAgent):
    name = AgentName.QUOTE
    system_prompt = SYSTEM
    max_tokens = 1500

    async def loop(self):
        msg = await self.receive(timeout=1.0)
        if not msg:
            return
        await self._handle(msg)

    async def _handle(self, msg: Message):
        from loguru import logger
        from core.skills.pricing_calculator import (
            estimate_price, detect_region, detect_site_type, extract_features
        )
        from core.skills.sector_kb import detect_sector
        logger.info(f"Teklif hazırlanıyor: {msg.content[:60]}")

        region   = detect_region(msg.content)
        stype    = detect_site_type(msg.content)
        sector   = detect_sector(msg.content)
        features = extract_features(msg.content)
        est      = estimate_price(region, stype, sector, features)

        price_hint = (
            f"[Pricing Calculation — Formula Estimate]\n"
            f"{est.summary()}\n"
            f"(Use this estimate as a reference, adjust based on brief details)"
        )

        quote = await self.ask(
            f"Project brief:\n{msg.content}\n\n"
            f"{price_hint}\n\n"
            "Prepare a detailed, professional quote for this project. "
            "Use the formula estimate as a guide but adjust based on the specific brief details."
        )

        self.save_observation(f"Teklif: {quote[:200]}", importance=8.5)
        await self.send(AgentName.MANAGER, MessageType.RESULT, quote)
