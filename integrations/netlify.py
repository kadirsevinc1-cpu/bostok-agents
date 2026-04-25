"""Netlify API — site oluştur, zip deploy et, URL al."""
import asyncio
import io
import os
import re
import zipfile
import aiohttp
from loguru import logger

NETLIFY_API = "https://api.netlify.com/api/v1"


class NetlifyClient:
    def __init__(self, token: str):
        self._token = token
        self._headers = {"Authorization": f"Bearer {token}"}

    async def deploy(self, site_dir: str, project_name: str) -> str:
        """Site klasörünü zip'le, Netlify'a yükle, canlı URL döndür."""
        zip_bytes = self._zip_directory(site_dir)
        site_id, site_url = await self._create_site(project_name)
        if not site_id:
            return ""
        return await self._deploy_zip(site_id, zip_bytes, site_url)

    def _zip_directory(self, directory: str) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(directory):
                for file in files:
                    filepath = os.path.join(root, file)
                    arcname = os.path.relpath(filepath, directory)
                    zf.write(filepath, arcname)
        return buf.getvalue()

    async def _create_site(self, project_name: str) -> tuple[str, str]:
        slug = re.sub(r"[^a-z0-9]", "-", project_name.lower())[:28].strip("-")
        name = f"bostok-{slug}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{NETLIFY_API}/sites",
                    json={"name": name},
                    headers=self._headers,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    data = await resp.json()
                    if resp.status not in (200, 201):
                        logger.error(f"Netlify site olusturma hata {resp.status}: {data}")
                        return "", ""
                    url = data.get("ssl_url") or data.get("url", "")
                    logger.info(f"Netlify site olusturuldu: {url}")
                    return data.get("id", ""), url
        except Exception as e:
            logger.error(f"Netlify create site hata: {e}")
            return "", ""

    async def _deploy_zip(self, site_id: str, zip_bytes: bytes, fallback_url: str) -> str:
        try:
            headers = {**self._headers, "Content-Type": "application/zip"}
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{NETLIFY_API}/sites/{site_id}/deploys",
                    data=zip_bytes,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as resp:
                    data = await resp.json()
                    if resp.status not in (200, 201):
                        logger.error(f"Netlify deploy hata {resp.status}: {data}")
                        return fallback_url
                    deploy_id = data.get("id", "")
                    site_url = data.get("deploy_ssl_url") or data.get("ssl_url") or fallback_url
                    if deploy_id:
                        site_url = await self._wait_ready(session, site_id, deploy_id, site_url)
                    return site_url
        except Exception as e:
            logger.error(f"Netlify zip deploy hata: {e}")
            return fallback_url

    async def _wait_ready(self, session, site_id: str, deploy_id: str, fallback: str) -> str:
        """Deploy 'ready' olana kadar bekle (max 3 dakika)."""
        for _ in range(18):
            await asyncio.sleep(10)
            try:
                async with session.get(
                    f"{NETLIFY_API}/sites/{site_id}/deploys/{deploy_id}",
                    headers=self._headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    data = await resp.json()
                    state = data.get("state", "")
                    if state == "ready":
                        return data.get("deploy_ssl_url") or data.get("ssl_url") or fallback
                    if state in ("error", "failed"):
                        logger.error(f"Netlify deploy basarisiz: {state}")
                        return ""
            except Exception:
                pass
        logger.warning("Netlify deploy timeout — URL tahmin ediliyor")
        return fallback


    async def deploy_demo_site(self, demo_dir: str) -> str:
        """
        demo_site/ klasörünü kalıcı bir Netlify sitesine deploy et.
        URL memory/demo_site_url.txt'de cache'lenir; geçerliyse yeniden deploy etmez.
        """
        from pathlib import Path
        import aiohttp as _aiohttp
        cache = Path("memory/demo_site_url.txt")

        # Cache kontrolü
        if cache.exists():
            cached = cache.read_text(encoding="utf-8").strip()
            if cached:
                try:
                    async with _aiohttp.ClientSession() as s:
                        async with s.head(cached, timeout=_aiohttp.ClientTimeout(total=6)) as r:
                            if r.status < 400:
                                logger.info(f"Demo site zaten aktif: {cached}")
                                return cached
                except Exception:
                    logger.warning("Demo site cache URL erişilemiyor, yeniden deploy ediliyor")

        # Deploy
        logger.info("Demo site Netlify'a deploy ediliyor...")
        zip_bytes = self._zip_directory(demo_dir)
        site_id, site_url = await self._create_site("bostok-demo-v2")
        if not site_id:
            return ""
        url = await self._deploy_zip(site_id, zip_bytes, site_url)
        if url:
            cache.parent.mkdir(exist_ok=True)
            cache.write_text(url, encoding="utf-8")
            logger.info(f"Demo site Netlify'da yayinda: {url}")
        return url


_client: NetlifyClient | None = None


def init_netlify() -> NetlifyClient | None:
    global _client
    try:
        from config import settings
        token = getattr(settings, "netlify_token", "")
        if token:
            _client = NetlifyClient(token)
            logger.info("Netlify bagli")
            return _client
    except Exception as e:
        logger.warning(f"Netlify init hata: {e}")
    return None


def get_netlify() -> NetlifyClient | None:
    return _client
