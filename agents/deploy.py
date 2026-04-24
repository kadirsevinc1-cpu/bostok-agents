"""Deploy Agent — üretilen siteyi Netlify'a yükler, canlı URL alır."""
from pathlib import Path
from agents.base import BaseAgent
from core.message_bus import AgentName, MessageType, Message

SYSTEM = """Sen Bostok.dev ajansının Deploy agent'ısın.
Görevin: Üretilen web sitelerini Netlify'a yüklemek ve canlı URL almak."""


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

        url = await netlify.deploy(site_dir, project_name)

        if url:
            logger.info(f"Deploy OK: {url}")
            self.save_observation(f"Site yayinda: {url}", importance=9.0)
            await self.send(
                AgentName.MANAGER, MessageType.RESULT,
                f"Site Netlify'da yayinda: {url}",
                {"project_name": project_name, "url": url},
            )
        else:
            await self.send(
                AgentName.MANAGER, MessageType.RESULT,
                f"Deploy basarisiz. Site yerel olarak hazir: {site_dir}",
                {"project_name": project_name, "url": "", "local_path": site_dir},
            )
