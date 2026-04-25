"""Semantic embedding — Cohere multilingual → Gemini → hash fallback."""
import math
import re
from loguru import logger

_HASH_DIM = 256


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def _hash_embed(text: str) -> list[float]:
    """API gerektirmeyen karakter n-gram hash embedding — fallback."""
    tokens = re.findall(r'\w+', text.lower())
    vec = [0.0] * _HASH_DIM
    for token in tokens:
        for n in (2, 3):
            for i in range(len(token) - n + 1):
                h = hash(token[i:i + n]) % _HASH_DIM
                vec[h] += 1.0
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


async def embed(texts: list[str]) -> list[list[float]]:
    """Cohere → Gemini → hash fallback sırasıyla dene."""
    if not texts:
        return []
    try:
        from config import settings
        if settings.cohere_api_key:
            result = await _cohere_embed(texts, settings.cohere_api_key)
            if result:
                logger.debug(f"Embedder: Cohere ({len(texts)} metin)")
                return result
        if settings.gemini_api_key:
            result = await _gemini_embed(texts, settings.gemini_api_key)
            if result:
                logger.debug(f"Embedder: Gemini ({len(texts)} metin)")
                return result
    except Exception as e:
        logger.debug(f"Embedder API hata: {e}")
    logger.debug(f"Embedder: hash fallback ({len(texts)} metin)")
    return [_hash_embed(t) for t in texts]


async def embed_one(text: str) -> list[float]:
    results = await embed([text[:1000]])
    return results[0] if results else []


async def _cohere_embed(texts: list[str], api_key: str) -> list[list[float]] | None:
    import aiohttp
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(
                "https://api.cohere.com/v1/embed",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "texts": [t[:512] for t in texts],
                    "model": "embed-multilingual-v3.0",
                    "input_type": "search_document",
                },
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    embs = data.get("embeddings")
                    if embs and len(embs) == len(texts):
                        return embs
    except Exception as e:
        logger.debug(f"Cohere embed hata: {e}")
    return None


async def _gemini_embed(texts: list[str], api_key: str) -> list[list[float]] | None:
    import aiohttp
    embeddings = []
    try:
        async with aiohttp.ClientSession() as s:
            for text in texts:
                async with s.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={api_key}",
                    json={"model": "models/text-embedding-004",
                          "content": {"parts": [{"text": text[:2000]}]}},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()
                    vals = data.get("embedding", {}).get("values", [])
                    if not vals:
                        return None
                    embeddings.append(vals)
        return embeddings
    except Exception as e:
        logger.debug(f"Gemini embed hata: {e}")
    return None
