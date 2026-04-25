"""Vercel deploy — demo_site/ klasörünü Vercel REST API ile deploy et."""
import asyncio
import base64
from pathlib import Path
from loguru import logger

VERCEL_API = "https://api.vercel.com"
_VERCEL_URL_CACHE = Path("memory/vercel_site_url.txt")


def _get_token() -> str:
    try:
        from config import settings
        return getattr(settings, "vercel_token", "")
    except Exception:
        return ""


async def deploy_demo_site(demo_dir: str) -> str:
    """
    demo_site/ klasörünü Vercel'e deploy et, URL döndür.
    Vercel REST API kullanır (CLI'dan bağımsız, token formatından bağımsız).
    """
    token = _get_token()
    if not token:
        logger.debug("VERCEL_TOKEN tanimli degil, Vercel deploy atlanıyor")
        return ""

    # Cache kontrolü
    if _VERCEL_URL_CACHE.exists():
        cached = _VERCEL_URL_CACHE.read_text(encoding="utf-8").strip()
        if cached:
            try:
                import aiohttp
                async with aiohttp.ClientSession() as s:
                    async with s.head(cached, timeout=aiohttp.ClientTimeout(total=6)) as r:
                        if r.status < 400:
                            logger.info(f"Vercel demo zaten aktif: {cached}")
                            return cached
            except Exception:
                pass

    logger.info("Vercel deploy basliyor...")
    try:
        url = await _api_deploy(demo_dir, token)
        if url:
            _VERCEL_URL_CACHE.parent.mkdir(exist_ok=True)
            _VERCEL_URL_CACHE.write_text(url, encoding="utf-8")
            logger.info(f"Vercel demo yayinda: {url}")
        return url
    except Exception as e:
        logger.warning(f"Vercel deploy hata: {e}")
        return ""


async def _api_deploy(demo_dir: str, token: str) -> str:
    """Vercel REST API v13 ile dosyaları deploy et."""
    import aiohttp

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # Dosyaları topla
    files = []
    base = Path(demo_dir).resolve()
    for fpath in base.rglob("*"):
        if not fpath.is_file():
            continue
        rel = fpath.relative_to(base).as_posix()
        raw = fpath.read_bytes()
        files.append({
            "file": rel,
            "data": base64.b64encode(raw).decode(),
            "encoding": "base64",
        })

    payload = {
        "name": "bostok-demo",
        "files": files,
        "target": "production",
        "projectSettings": {
            "framework": None,
            "outputDirectory": None,
            "buildCommand": None,
            "installCommand": None,
            "devCommand": None,
        },
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{VERCEL_API}/v13/deployments",
            json=payload,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=60),
        ) as resp:
            data = await resp.json()
            if resp.status not in (200, 201):
                logger.warning(f"Vercel API hata {resp.status}: {data.get('error', data)}")
                return ""

            deploy_id = data.get("id", "")
            url = data.get("url", "")
            if url and not url.startswith("http"):
                url = f"https://{url}"

            if deploy_id:
                url = await _wait_ready(session, deploy_id, headers, url)

            # SSO korumasını kapat — herkese açık olsun
            await _disable_protection(session, headers)

            return url


async def _disable_protection(session, headers: dict):
    """Proje SSO/authentication korumasını kapat (public erişim)."""
    import aiohttp
    try:
        async with session.patch(
            f"{VERCEL_API}/v9/projects/bostok-demo",
            json={"ssoProtection": None},
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status == 200:
                logger.debug("Vercel SSO korumasi kapatildi")
    except Exception:
        pass


async def _wait_ready(session, deploy_id: str, headers: dict, fallback: str) -> str:
    """Deploy 'READY' olana kadar bekle (max 2 dakika)."""
    import aiohttp
    for _ in range(24):
        await asyncio.sleep(5)
        try:
            async with session.get(
                f"{VERCEL_API}/v13/deployments/{deploy_id}",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                data = await resp.json()
                state = data.get("readyState") or data.get("state", "")
                if state == "READY":
                    url = data.get("url", fallback)
                    if url and not url.startswith("http"):
                        url = f"https://{url}"
                    return url
                if state in ("ERROR", "CANCELED"):
                    logger.error(f"Vercel deploy basarisiz: {state}")
                    return ""
        except Exception:
            pass
    logger.warning("Vercel deploy timeout — URL tahmin ediliyor")
    return fallback


def get_vercel_url() -> str:
    if _VERCEL_URL_CACHE.exists():
        return _VERCEL_URL_CACHE.read_text(encoding="utf-8").strip()
    return ""
