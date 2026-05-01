"""
CompetitorAnalystAgent — hunts competitor sites and generates a winning website concept.
Triggered by /hunt Telegram command.
"""
import json
from pathlib import Path
from datetime import datetime
from loguru import logger
from agents.base import BaseAgent
from core.message_bus import AgentName, MessageType, Message

SYSTEM = """You are a competitive website analyst and web strategist at Bostok.dev.
Analyze competitor websites objectively and produce specific, commercially viable website concepts.
Focus on conversion-driving elements: hero copy, CTAs, trust signals, section order.
Be concise, data-driven, and actionable."""


class CompetitorAnalystAgent(BaseAgent):
    name = AgentName.COMPETITOR_ANALYST
    system_prompt = SYSTEM
    max_tokens = 1400

    async def loop(self):
        msg = await self.receive(timeout=1.0)
        if msg:
            await self._handle(msg)

    async def _handle(self, msg: Message):
        meta    = msg.metadata or {}
        sector  = meta.get("sector", "").strip()
        country = meta.get("country", "").strip()

        if not sector or not country:
            logger.warning("CompetitorAnalyst: missing sector/country")
            return

        await self.send(
            AgentName.SYSTEM, MessageType.USER_NOTIFY,
            f"🔍 <b>Website Hunt başladı</b>\n"
            f"Sektör: <b>{sector}</b> | Ülke: <b>{country}</b>\n"
            f"Rakip siteler taranıyor, lütfen bekleyin..."
        )

        try:
            from integrations.site_hunter import run_hunt
            analyses = await run_hunt(sector, country, max_sites=10)
        except Exception as e:
            logger.error(f"CompetitorAnalyst: hunt failed: {e}")
            await self.send(AgentName.SYSTEM, MessageType.USER_NOTIFY, f"❌ Hunt hatası: {e}")
            return

        if not analyses:
            await self.send(
                AgentName.SYSTEM, MessageType.USER_NOTIFY,
                f"❌ <b>Hiç site bulunamadı.</b>\n"
                f"Arama terimi daha genel dene: <code>/hunt {sector} Europe</code>"
            )
            return

        # Build competitor summary for LLM
        blocks = []
        for i, a in enumerate(analyses, 1):
            blocks.append(
                f"--- Site {i}: {a['url']} ---\n"
                f"Title: {a['title']}\n"
                f"H1: {' | '.join(a['h1']) or '(none)'}\n"
                f"Navigation: {', '.join(a['nav'][:7]) or '(none)'}\n"
                f"CTAs found: {', '.join(a['ctas'][:5]) or '(none)'}\n"
                f"Color palette: {', '.join(a['colors']) or '(none)'}\n"
                f"Meta desc: {a['meta'][:120]}\n"
                f"Contact form: {a['has_form']} | WhatsApp: {a['has_whatsapp']} | Live chat: {a['has_chat']}"
            )

        prompt = f"""You analyzed {len(analyses)} competitor websites in this market:
Sector: {sector}
Market/Country: {country}

=== COMPETITOR DATA ===
{chr(10).join(blocks)}

=== TASK ===
Produce a winning website concept for a new entrant that outperforms these competitors.

Structure your output EXACTLY as:

**COMPETITIVE GAPS** (what competitors are missing or doing badly — 3 bullets max)

**HERO SECTION**
Headline: [short, specific, benefit-driven — NOT generic]
Subheadline: [1-2 sentences that remove objections]
Primary CTA: [button text — strong action verb]
Secondary CTA: [softer option]

**PAGE SECTIONS** (ordered, each with 1-line purpose)
1. ...
2. ...
(etc.)

**TRUST ELEMENTS** (social proof, certs, guarantees — pick the most relevant for this sector)

**COLOR PALETTE**
Primary: #XXXXXX — [emotion/association]
Secondary: #XXXXXX — [emotion/association]
Accent: #XXXXXX — [emotion/association]

**KEY DIFFERENTIATOR**
[One punchy sentence: what makes this site stand out]

Write in English. Be specific to the {sector} sector in {country}."""

        logger.info(f"CompetitorAnalyst: LLM concept for {sector}/{country}")
        try:
            concept = await self.ask(prompt)
        except Exception as e:
            logger.error(f"CompetitorAnalyst: LLM error: {e}")
            await self.send(AgentName.SYSTEM, MessageType.USER_NOTIFY, f"❌ LLM hatası: {e}")
            return

        # Persist to JSONL
        log_path = Path("memory/site_analyses.jsonl")
        log_path.parent.mkdir(exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts":       datetime.now().isoformat(),
                "sector":   sector,
                "country":  country,
                "n_sites":  len(analyses),
                "sites":    analyses,
                "concept":  concept,
            }, ensure_ascii=False) + "\n")

        # Telegram notification — split if too long
        header = (
            f"🎯 <b>Website Concept — {sector} / {country}</b>\n"
            f"<i>{len(analyses)} rakip analiz edildi</i>\n\n"
        )
        body = concept[:3800] if len(concept) > 3800 else concept
        tail = "\n\n<i>(Tam analiz: memory/site_analyses.jsonl)</i>" if len(concept) > 3800 else ""

        await self.send(AgentName.SYSTEM, MessageType.USER_NOTIFY, header + body + tail)
        logger.info(f"CompetitorAnalyst: concept delivered for {sector}/{country}")

        # Demo mode: forward concept directly to Developer for site build
        if meta.get("demo_mode"):
            await self.send(AgentName.SYSTEM, MessageType.USER_NOTIFY,
                            f"🔨 <b>Demo site inşa ediliyor:</b> {sector}...")
            await self.send(
                AgentName.DEVELOPER, MessageType.TASK,
                concept,
                {"demo_build": True, "sector": sector, "country": country},
            )
