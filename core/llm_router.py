"""
LLM Router — Çoklu provider, sıralı fallback, akıllı limit yönetimi.
Sıra: Groq → Cerebras → Gemini → Mistral → Sambanova → OpenRouter → Cohere → DeepSeek → Claude

Limit davranışı:
- Rate limit (429 / per-minute) → kısa cooldown (60s varsayılan)
- Günlük kota (daily / quota / exceeded) → UTC gece yarısına kadar cooldown
- retry-after header'ı varsa tam süre beklenir
- Provider cooldown'dan çıkınca INFO logu yazılır
"""
import asyncio
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from loguru import logger


@dataclass
class ProviderConfig:
    name:       str
    api_key:    str
    base_url:   str
    model:      str
    backend:    str                    # "openai" | "gemini" | "anthropic"
    headers:    dict = None            # opsiyonel ek header (OpenRouter vb.)


def _build_providers() -> list[ProviderConfig]:
    from config import settings
    providers = []

    if settings.groq_api_key:
        providers.append(ProviderConfig(
            name="Groq", api_key=settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
            model="llama-3.1-8b-instant", backend="openai",
        ))

    if settings.cerebras_api_key:
        providers.append(ProviderConfig(
            name="Cerebras", api_key=settings.cerebras_api_key,
            base_url="https://api.cerebras.ai/v1",
            model="llama3.1-8b", backend="openai",
        ))

    if settings.gemini_api_key:
        providers.append(ProviderConfig(
            name="Gemini", api_key=settings.gemini_api_key,
            base_url="", model="gemini-2.0-flash-lite", backend="gemini",
        ))

    if settings.mistral_api_key:
        providers.append(ProviderConfig(
            name="Mistral", api_key=settings.mistral_api_key,
            base_url="https://api.mistral.ai/v1",
            model="mistral-small-latest", backend="openai",
        ))

    if settings.sambanova_api_key:
        providers.append(ProviderConfig(
            name="Sambanova", api_key=settings.sambanova_api_key,
            base_url="https://api.sambanova.ai/v1",
            model="Meta-Llama-3.1-8B-Instruct", backend="openai",
        ))

    if settings.openrouter_api_key:
        providers.append(ProviderConfig(
            name="OpenRouter", api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            model="meta-llama/llama-3.1-8b-instruct:free", backend="openai",
            headers={"HTTP-Referer": "https://bostok.dev", "X-Title": "Bostok Agents"},
        ))

    if settings.cohere_api_key:
        providers.append(ProviderConfig(
            name="Cohere", api_key=settings.cohere_api_key,
            base_url="https://api.cohere.com/compatibility/v1",
            model="command-r-08-2024", backend="openai",
        ))

    if settings.deepseek_api_key:
        providers.append(ProviderConfig(
            name="DeepSeek", api_key=settings.deepseek_api_key,
            base_url="https://api.deepseek.com",
            model="deepseek-chat", backend="openai",
        ))

    if settings.anthropic_api_key:
        providers.append(ProviderConfig(
            name="Claude", api_key=settings.anthropic_api_key,
            base_url="", model="claude-haiku-4-5-20251001", backend="anthropic",
        ))

    return providers


def _parse_cooldown_seconds(err: str) -> float:
    """
    Hata mesajından bekleme süresini çıkar.
    - 'retry after X' / 'retry-after: X' → X saniye
    - 'daily' / 'quota' / 'exceeded' → UTC gece yarısına kadar
    - '429' / 'rate limit' → 60s
    - Diğer → 30s
    """
    err_lower = err.lower()

    # Açık retry-after süresi
    m = re.search(r"retry[_\-\s]{0,5}after[^0-9]{0,10}(\d+)", err_lower)
    if m:
        return min(float(m.group(1)), 7200)

    m = re.search(r"(\d+)\s*second", err_lower)
    if m:
        return min(float(m.group(1)), 7200)

    # Günlük kota
    if any(w in err_lower for w in ["daily", "quota", "exceeded", "per day", "limit reached", "per_day"]):
        now = datetime.now(timezone.utc)
        next_midnight = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=5, microsecond=0
        )
        secs = (next_midnight - now).total_seconds()
        logger.warning(f"Gunluk kota limiti — {secs/3600:.1f} saat cooldown")
        return max(secs, 300)

    # Per-minute / rate limit
    if "429" in err or "rate" in err_lower or "too many" in err_lower:
        return 60

    return 30


async def _call_openai(cfg: ProviderConfig, messages: list[dict], max_tokens: int) -> str | None:
    from openai import AsyncOpenAI
    client = AsyncOpenAI(
        api_key=cfg.api_key,
        base_url=cfg.base_url,
        default_headers=cfg.headers or {},
    )
    resp = await client.chat.completions.create(
        model=cfg.model, messages=messages, max_tokens=max_tokens
    )
    tokens = resp.usage.total_tokens if resp.usage else 0
    _record_tokens(tokens, cfg.name)
    return resp.choices[0].message.content or None


async def _call_gemini(cfg: ProviderConfig, messages: list[dict], max_tokens: int) -> str | None:
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=cfg.api_key)
    parts = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "") or ""
        if not content.strip():
            continue
        if role == "system":
            parts.append(f"[TALİMAT]\n{content}")
        elif role == "user":
            parts.append(f"Kullanıcı: {content}")
        elif role == "assistant":
            parts.append(f"Asistan: {content}")
    prompt = "\n\n".join(parts)
    response = await asyncio.to_thread(
        client.models.generate_content,
        model=cfg.model,
        contents=prompt,
        config=types.GenerateContentConfig(max_output_tokens=max_tokens, temperature=0.3),
    )
    tokens = response.usage_metadata.total_token_count if response.usage_metadata else 0
    _record_tokens(tokens, cfg.name)
    return response.text.strip() if response.text else None


async def _call_anthropic(cfg: ProviderConfig, messages: list[dict], max_tokens: int) -> str | None:
    import anthropic
    client = anthropic.AsyncAnthropic(api_key=cfg.api_key)
    system = next((m["content"] for m in messages if m["role"] == "system"), "")
    msgs = [m for m in messages if m["role"] != "system"]
    resp = await client.messages.create(
        model=cfg.model, max_tokens=max_tokens, system=system, messages=msgs
    )
    tokens = resp.usage.input_tokens + resp.usage.output_tokens
    _record_tokens(tokens, cfg.name)
    return resp.content[0].text or None


def _record_tokens(tokens: int, provider: str):
    try:
        from core.budget import budget
        budget.record(tokens, provider)
    except Exception:
        pass


class LLMRouter:
    def __init__(self):
        self._providers: list[ProviderConfig] = []
        self._cooldowns: dict[str, float] = {}   # name → monotonic reset time
        self._cooling: set[str] = set()           # şu an cooldown'da olanlar
        self._active: str | None = None           # son başarılı provider
        self._initialized = False

    def _ensure_init(self):
        if self._initialized:
            return
        self._providers = _build_providers()
        names = [p.name for p in self._providers]
        logger.info(f"LLM Router: {names} hazir")
        self._initialized = True

    def _available(self) -> list[ProviderConfig]:
        now = time.monotonic()
        result = []
        for p in self._providers:
            cd = self._cooldowns.get(p.name, 0)
            if cd < now:
                if p.name in self._cooling:
                    self._cooling.discard(p.name)
                    self._cooldowns[p.name] = 0
                    logger.info(f"LLM: {p.name} cooldown bitti, havuza geri dondu")
                result.append(p)
        return result

    def _set_cooldown(self, name: str, seconds: float):
        self._cooldowns[name] = time.monotonic() + seconds
        self._cooling.add(name)
        logger.warning(f"LLM: {name} {seconds:.0f}s cooldown'a alindi")
        if self._active == name:
            self._active = None

    async def chat(self, messages: list[dict], max_tokens: int = 1024, heavy: bool = False) -> str:
        self._ensure_init()

        from core.budget import budget
        if budget.is_blocked():
            return "Gunluk token limitine ulasildi."

        for provider in self._available():
            if self._active and self._active != provider.name:
                logger.info(f"LLM: {self._active} → {provider.name} geciliyor")

            logger.debug(f"LLM: {provider.name}/{provider.model} deneniyor")
            try:
                if provider.backend == "openai":
                    result = await _call_openai(provider, messages, max_tokens)
                elif provider.backend == "gemini":
                    result = await _call_gemini(provider, messages, max_tokens)
                elif provider.backend == "anthropic":
                    result = await _call_anthropic(provider, messages, max_tokens)
                else:
                    continue

                if result:
                    if self._active != provider.name:
                        logger.info(f"LLM: Aktif provider = {provider.name}")
                        self._active = provider.name
                    logger.debug(f"LLM: {provider.name} yanit verdi")
                    return result
                else:
                    logger.warning(f"LLM: {provider.name} bos yanit dondu")
                    self._set_cooldown(provider.name, 30)

            except Exception as e:
                err = str(e)
                logger.warning(f"LLM: {provider.name} hata: {err[:120]}")
                seconds = _parse_cooldown_seconds(err)
                self._set_cooldown(provider.name, seconds)

        logger.error("LLM Router: Tum providerlar basarisiz veya cooldown'da")
        return "LLM yanit veremedi, lutfen tekrar deneyin."

    def status(self) -> str:
        """Mevcut provider durumunu özetler."""
        now = time.monotonic()
        lines = [f"Aktif: {self._active or 'yok'}"]
        for p in self._providers:
            cd = self._cooldowns.get(p.name, 0)
            if cd > now:
                remaining = cd - now
                lines.append(f"  {p.name}: cooldown {remaining:.0f}s kaldi")
            else:
                lines.append(f"  {p.name}: hazir")
        return "\n".join(lines)


router = LLMRouter()
