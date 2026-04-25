"""Netlify API — site oluştur veya mevcut siteyi güncelle, zip deploy et, URL al."""
import asyncio
import io
import os
import re
import zipfile
import aiohttp
from pathlib import Path
from loguru import logger

NETLIFY_API = "https://api.netlify.com/api/v1"
_DEMO_ID_CACHE   = Path("memory/demo_site_id.txt")
_DEMO_URL_CACHE  = Path("memory/demo_site_url.txt")


class NetlifyClient:
    def __init__(self, token: str):
        self._token = token
        self._headers = {"Authorization": f"Bearer {token}"}

    # ── Genel deploy ─────────────────────────────────────────────────────────

    async def deploy(self, site_dir: str, project_name: str) -> str:
        """Site klasörünü zip'le, Netlify'a yükle, canlı URL döndür."""
        zip_bytes = self._zip_directory(site_dir)
        site_id, site_url = await self._get_or_create_site(project_name)
        if not site_id:
            return ""
        return await self._deploy_zip(site_id, zip_bytes, site_url)

    # ── Demo site deploy ─────────────────────────────────────────────────────

    async def deploy_demo_site(self, demo_dir: str) -> str:
        """
        demo_site/ klasörünü kalıcı bir Netlify sitesine deploy et.
        - URL cache geçerliyse deploy etmez, direkt döner.
        - Site ID cache varsa aynı siteye deploy eder (yeni site OLUŞTURMAZ).
        - İkisi de yoksa mevcut sitelerde "bostok-demo" arar, bulamazsa oluşturur.
        """
        # 1. URL cache kontrolü — hâlâ erişilebiliyorsa dokunma
        if _DEMO_URL_CACHE.exists():
            cached_url = _DEMO_URL_CACHE.read_text(encoding="utf-8").strip()
            if cached_url:
                try:
                    async with aiohttp.ClientSession() as s:
                        async with s.head(cached_url, timeout=aiohttp.ClientTimeout(total=6)) as r:
                            if r.status < 400:
                                logger.info(f"Demo site zaten aktif: {cached_url}")
                                return cached_url
                except Exception:
                    logger.warning("Demo site URL erişilemiyor, yeniden deploy ediliyor")

        # 2. Site ID cache — mevcut siteye deploy et (yeni site oluşturma)
        site_id = ""
        site_url = ""
        if _DEMO_ID_CACHE.exists():
            site_id = _DEMO_ID_CACHE.read_text(encoding="utf-8").strip()
            if site_id:
                # Disabled site'a deploy etme — zaman kaybı + URL çalışmaz
                if await self._is_site_disabled(site_id):
                    logger.warning(f"Demo site disabled (Netlify dashboard'dan enable et): {site_id}")
                    return ""
                site_url = await self._get_site_url(site_id)
                logger.info(f"Demo site ID cache: {site_id}")

        # 3. ID yoksa Netlify'da "bostok-demo" adlı siteyi ara
        if not site_id:
            site_id, site_url = await self._find_existing_site("bostok-demo")

        # 4. NETLIFY_DEMO_SITE_ID env var varsa onu kullan
        if not site_id:
            try:
                from config import settings
                env_id = getattr(settings, "netlify_demo_site_id", "")
                if env_id:
                    if await self._is_site_disabled(env_id):
                        logger.warning(f"NETLIFY_DEMO_SITE_ID disabled, Worker kullaniliyor")
                        return ""
                    site_id  = env_id
                    site_url = await self._get_site_url(site_id)
                    logger.info(f"Demo site env'den alindi: {site_id}")
            except Exception:
                pass

        # 5. Hâlâ yoksa oluşturmayı dene; 422 gelirse Worker'a bırak
        if not site_id:
            logger.info("Demo site bulunamadi, olusturulmaya calisiliyor...")
            site_id, site_url = await self._create_site("bostok-demo")

        if not site_id:
            logger.warning("Demo site Netlify'a yuklenemedi — Worker URL kullanilacak")
            return ""

        # ID'yi cache'le
        _DEMO_ID_CACHE.parent.mkdir(exist_ok=True)
        _DEMO_ID_CACHE.write_text(site_id, encoding="utf-8")

        # Deploy
        logger.info(f"Demo site deploy ediliyor (site: {site_id})...")
        zip_bytes = self._zip_directory(demo_dir)
        url = await self._deploy_zip(site_id, zip_bytes, site_url)
        # Sadece gerçekten erişilebilirse cache'le
        if url:
            try:
                async with aiohttp.ClientSession() as s:
                    async with s.head(url, timeout=aiohttp.ClientTimeout(total=8)) as r:
                        if r.status < 400:
                            _DEMO_URL_CACHE.parent.mkdir(exist_ok=True)
                            _DEMO_URL_CACHE.write_text(url, encoding="utf-8")
                            logger.info(f"Demo site yayinda: {url}")
                            return url
            except Exception:
                pass
            logger.warning(f"Deploy URL erişilemiyor ({url}) — Worker kullanilacak")
        return ""

    # ── Yardımcı metodlar ─────────────────────────────────────────────────────

    def _zip_directory(self, directory: str) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(directory):
                for file in files:
                    filepath = os.path.join(root, file)
                    arcname = os.path.relpath(filepath, directory)
                    zf.write(filepath, arcname)
        return buf.getvalue()

    async def _is_site_disabled(self, site_id: str) -> bool:
        """Site disabled mi? Disabled sitelere deploy etme."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{NETLIFY_API}/sites/{site_id}",
                    headers=self._headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return bool(data.get("disabled", False))
        except Exception:
            pass
        return False

    async def _find_existing_site(self, name_prefix: str) -> tuple[str, str]:
        """Hesaptaki siteler arasında name_prefix ile başlayan ilkini bul."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{NETLIFY_API}/sites",
                    headers=self._headers,
                    params={"per_page": 100},
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        return "", ""
                    sites = await resp.json()
                    for site in sites:
                        if site.get("name", "").startswith(name_prefix):
                            sid  = site.get("id", "")
                            surl = site.get("ssl_url") or site.get("url", "")
                            logger.info(f"Mevcut Netlify sitesi bulundu: {site['name']} ({sid})")
                            return sid, surl
        except Exception as e:
            logger.warning(f"Netlify site listesi alınamadı: {e}")
        return "", ""

    async def _get_site_url(self, site_id: str) -> str:
        """Site ID'den URL al."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{NETLIFY_API}/sites/{site_id}",
                    headers=self._headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("ssl_url") or data.get("url", "")
        except Exception:
            pass
        return ""

    async def _get_or_create_site(self, project_name: str) -> tuple[str, str]:
        """Önce mevcut site ara, yoksa oluştur."""
        slug = re.sub(r"[^a-z0-9]", "-", project_name.lower())[:28].strip("-")
        name = f"bostok-{slug}"
        existing = await self._find_existing_site(name)
        if existing[0]:
            return existing
        return await self._create_site(project_name)

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
                    site_url  = data.get("deploy_ssl_url") or data.get("ssl_url") or fallback_url
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
