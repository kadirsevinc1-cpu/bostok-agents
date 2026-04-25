"""Vercel deploy — demo_site/ klasörünü Vercel'e deploy et, URL al."""
import asyncio
import json
import os
import subprocess
from pathlib import Path
from loguru import logger

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
    - URL cache geçerliyse dokunma.
    - `npx vercel --prod --yes --token <TOKEN>` ile deploy et.
    - VERCEL_TOKEN .env'de yoksa "" döner.
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
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, _run_deploy, demo_dir, token)
        if result:
            _VERCEL_URL_CACHE.parent.mkdir(exist_ok=True)
            _VERCEL_URL_CACHE.write_text(result, encoding="utf-8")
            logger.info(f"Vercel demo yayinda: {result}")
        return result
    except Exception as e:
        logger.warning(f"Vercel deploy hata: {e}")
        return ""


def _run_deploy(demo_dir: str, token: str) -> str:
    """Vercel CLI ile deploy (blocking — executor'da çalışır)."""
    cmd = [
        "npx", "vercel",
        "--prod", "--yes",
        "--token", token,
        "--name", "bostok-demo",
        demo_dir,
    ]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120,
            cwd=str(Path(demo_dir).parent),
        )
        output = proc.stdout.strip()
        # Son satır deployment URL'i
        lines = [l.strip() for l in output.splitlines() if l.strip().startswith("http")]
        if lines:
            url = lines[-1]
            logger.info(f"Vercel deploy tamamlandi: {url}")
            return url
        if proc.returncode != 0:
            logger.warning(f"Vercel CLI hata (exit {proc.returncode}): {proc.stderr[:300]}")
    except subprocess.TimeoutExpired:
        logger.warning("Vercel deploy timeout (120s)")
    except Exception as e:
        logger.warning(f"Vercel CLI calıstırılamadi: {e}")
    return ""


def get_vercel_url() -> str:
    if _VERCEL_URL_CACHE.exists():
        return _VERCEL_URL_CACHE.read_text(encoding="utf-8").strip()
    return ""
