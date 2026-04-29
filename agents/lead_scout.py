"""LeadScoutAgent — 7/24 lead önbelleği doldurur; marketing agent'a hazır lead bırakır."""
import asyncio
import datetime as _dt
import json as _json
from pathlib import Path as _Path

from loguru import logger
from agents.base import BaseAgent
from core.message_bus import AgentName


_IDX_FILE = _Path("memory/scout_idx.json")


class LeadScoutAgent(BaseAgent):
    name = AgentName.LEAD_SCOUT
    system_prompt = "Lead Scout"
    max_tokens = 100

    def __init__(self):
        super().__init__()
        self._idx: int = self._load_idx()
        self._pairs: list[tuple[str, str]] = self._build_pairs()
        logger.info(f"LeadScout hazir: {len(self._pairs)} sektor/lokasyon kombinasyonu, idx={self._idx}")

    def _load_idx(self) -> int:
        try:
            if _IDX_FILE.exists():
                return int(_json.loads(_IDX_FILE.read_text(encoding="utf-8")))
        except Exception:
            pass
        return 0

    def _save_idx(self):
        _IDX_FILE.parent.mkdir(exist_ok=True)
        tmp = _IDX_FILE.with_suffix(".tmp")
        tmp.write_text(_json.dumps(self._idx), encoding="utf-8")
        import os
        os.replace(tmp, _IDX_FILE)

    def _build_pairs(self) -> list[tuple[str, str]]:
        from core.campaigns import CAMPAIGNS
        pairs = []
        for c in CAMPAIGNS:
            for loc in c["locations"]:
                pairs.append((c["sector"], loc))
        return pairs

    async def loop(self):
        if not self._pairs:
            await self._chunked_sleep(3600)
            return

        sector, location = self._pairs[self._idx % len(self._pairs)]
        self._idx += 1
        self._save_idx()

        await self._prefetch(sector, location)

        # Tüm kombinasyonları bitirdik → biraz daha uzun bekle
        if self._idx % len(self._pairs) == 0:
            logger.info(f"LeadScout tur tamamlandi: {len(self._pairs)} kombinasyon tarand?")
            await self._chunked_sleep(1800)
        else:
            # Kombinasyonlar arası: API hız sınırına takılmamak için bekle
            await self._chunked_sleep(90)

    async def _prefetch(self, sector: str, location: str):
        from integrations.lead_finder import find_leads, _get_cached_leads
        from config import settings

        # Cache zaten taze mi?
        cached = _get_cached_leads(sector, location)
        if cached is not None:
            logger.debug(f"LeadScout cache hit, atlanıyor: {sector}/{location}")
            return

        api_key = getattr(settings, "google_maps_api_key", "")
        try:
            leads = await find_leads(sector, location, api_key)
            email_count = sum(1 for l in leads if l.email)
            logger.info(
                f"LeadScout: {sector}/{location} → {len(leads)} lead, "
                f"{email_count} email bulundu"
            )
        except Exception as e:
            logger.warning(f"LeadScout hata [{sector}/{location}]: {e}")

    async def _chunked_sleep(self, total: int):
        chunk = 30
        for _ in range(total // chunk):
            if not self.running:
                return
            self.last_heartbeat = _dt.datetime.now()
            await asyncio.sleep(chunk)
        remainder = total % chunk
        if remainder > 0:
            await asyncio.sleep(remainder)
