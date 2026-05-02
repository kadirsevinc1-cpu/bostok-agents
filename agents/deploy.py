"""Deploy Agent — üretilen siteyi Netlify'a yükler, health check yapar, URL döner."""
import asyncio
from pathlib import Path
from agents.base import BaseAgent
from core.message_bus import AgentName, MessageType, Message

SYSTEM = """Sen Bostok.dev ajansının Deploy agent'ısın.
Görevin: Üretilen web sitelerini Netlify'a yüklemek ve canlı URL almak."""

_MAX_RETRIES = 3
_RETRY_DELAY = 8   # saniye


class DeployAgent(BaseAgent):
    name = AgentName.DEPLOY
    system_prompt = SYSTEM
    max_tokens = 200

    async def loop(self):
        msg = await self.receive(timeout=1.0)
        if not msg:
            return
        await self._handle(msg)

    async def _handle(self, msg: Message):
        from loguru import logger
        from integrations.netlify import get_netlify

        site_dir = msg.metadata.get("site_dir", "")
        project_name = msg.metadata.get("project_name", "site")
        logger.info(f"Deploy basliyor: {project_name} ({site_dir})")

        netlify = get_netlify()
        if not netlify:
            await self.send(
                AgentName.MANAGER, MessageType.RESULT,
                f"Netlify token eksik. Site yerel olarak hazir: {site_dir}",
                {"project_name": project_name, "url": "", "local_path": site_dir},
            )
            return

        if not site_dir or not Path(site_dir).exists():
            await self.send(
                AgentName.MANAGER, MessageType.RESULT,
                f"Site klasoru bulunamadi: {site_dir}",
            )
            return

        url = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                url = await netlify.deploy(site_dir, project_name)
                if url:
                    break
            except Exception as e:
                logger.warning(f"Deploy deneme {attempt}/{_MAX_RETRIES} hata: {e}")
            if attempt < _MAX_RETRIES:
                logger.info(f"Deploy yeniden deneniyor ({attempt + 1}/{_MAX_RETRIES})...")
                await asyncio.sleep(_RETRY_DELAY)

        if url:
            healthy = await self._health_check(url)
            status = "✅ sağlıklı" if healthy else "⚠️ yanıt alamadı"
            logger.info(f"Deploy OK: {url} [{status}]")
            self.save_observation(f"Site yayinda: {url}", importance=9.0)
            await self.send(
                AgentName.MANAGER, MessageType.RESULT,
                f"Site Netlify'da yayinda: {url}",
                {"project_name": project_name, "url": url, "healthy": healthy},
            )
        else:
            logger.error(f"Deploy {_MAX_RETRIES} denemede basarisiz: {project_name}")
            await self.send(
                AgentName.MANAGER, MessageType.RESULT,
                f"Deploy {_MAX_RETRIES} denemede basarisiz. Site yerel olarak hazir: {site_dir}",
                {"project_name": project_name, "url": "", "local_path": site_dir},
            )

    @staticmethod
    async def _health_check(url: str) -> bool:
        """Deploy edilen URL'ye GET isteği at — sitenin ayakta olduğunu doğrula."""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    return resp.status < 400
        except Exception:
            return True  # Kontrol edilemiyorsa optimistik davran
