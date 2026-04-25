"""
LLM Router — Çoklu provider, sıralı fallback.
Sıra: Groq → Cerebras → DeepSeek → Gemini → Mistral → Claude
"""
import asyncio
import time
from dataclasses import dataclass
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
    """
    Provider öncelik sırası (ücretsizler önce, ücretliler sonda):
    Groq → Cerebras → Gemini → Mistral → Sambanova → OpenRouter → Cohere → DeepSeek → Claude
    """
    from config import settings
    providers = []

    # ── 1. Groq — ücretsiz, hızlı ─────────────────────────────────
    if settings.groq_api_key:
        providers.append(ProviderConfig(
            name="Groq", api_key=settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
            model="llama-3.1-8b-instant", backend="openai",
        ))

    # ── 2. Cerebras — ücretsiz, çok hızlı ────────────────────────
    if settings.cerebras_api_key:
        providers.append(ProviderConfig(
            name="Cerebras", api_key=settings.cerebras_api_key,
            base_url="https://api.cerebras.ai/v1",
            model="llama3.1-8b", backend="openai",
        ))

    # ── 3. Gemini — ücretsiz, 1M token/gün ───────────────────────
    if settings.gemini_api_key:
        providers.append(ProviderConfig(
            name="Gemini", api_key=settings.gemini_api_key,
            base_url="", model="gemini-2.0-flash-lite", backend="gemini",
        ))

    # ── 4. Mistral — ücretsiz tier ────────────────────────────────
    if settings.mistral_api_key:
        providers.append(ProviderConfig(
            name="Mistral", api_key=settings.mistral_api_key,
            base_url="https://api.mistral.ai/v1",
            model="mistral-small-latest", backend="openai",
        ))

    # ── 5. Sambanova — ücretsiz tier, hızlı ─────────────────────
    if settings.sambanova_api_key:
        providers.append(ProviderConfig(
            name="Sambanova", api_key=settings.sambanova_api_key,
            base_url="https://api.sambanova.ai/v1",
            model="Meta-Llama-3.1-8B-Instruct", backend="openai",
        ))

    # ── 6. OpenRouter (ücretsiz modeller) ────────────────────────
    if settings.openrouter_api_key:
        providers.append(ProviderConfig(
            name="OpenRouter", api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            model="meta-llama/llama-3.1-8b-instruct:free", backend="openai",
            headers={"HTTP-Referer": "https://bostok.dev", "X-Title": "Bostok Agents"},
        ))

    # ── 7. Cohere — ücretsiz tier (1000 çağrı/ay) ────────────────
    if settings.cohere_api_key:
        providers.append(ProviderConfig(
            name="Cohere", api_key=settings.cohere_api_key,
            base_url="https://api.cohere.com/compatibility/v1",
            model="command-r-08-2024", backend="openai",
        ))

    # ── 8. DeepSeek — ücretli, sparingly kullan ──────────────────
    if settings.deepseek_api_key:
        providers.append(ProviderConfig(
            name="DeepSeek", api_key=settings.deepseek_api_key,
            base_url="https://api.deepseek.com",
            model="deepseek-chat", backend="openai",
        ))

    # ── 9. Claude — ücretli, son çare ────────────────────────────
    if settings.anthropic_api_key:
        providers.append(ProviderConfig(
            name="Claude", api_key=settings.anthropic_api_key,
            base_url="", model="claude-haiku-4-5-20251001", backend="anthropic",
        ))

    return providers


async def _call_openai(cfg: ProviderConfig, messages: list[dict], max_tokens: int) -> str | None:
    try:
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
        return resp.choices[0].message.content or ""
    except Exception as e:
        logger.warning(f"{cfg.name} hata: {str(e)[:120]}")
        return None


async def _call_gemini(cfg: ProviderConfig, messages: list[dict], max_tokens: int) -> str | None:
    try:
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
        return response.text.strip() if response.text else ""
    except Exception as e:
        logger.warning(f"Gemini hata: {str(e)[:120]}")
        return None


async def _call_anthropic(cfg: ProviderConfig, messages: list[dict], max_tokens: int) -> str | None:
    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=cfg.api_key)
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        msgs = [m for m in messages if m["role"] != "system"]
        resp = await client.messages.create(
            model=cfg.model, max_tokens=max_tokens, system=system, messages=msgs
        )
        tokens = resp.usage.input_tokens + resp.usage.output_tokens
        _record_tokens(tokens, cfg.name)
        return resp.content[0].text
    except Exception as e:
        logger.warning(f"Claude hata: {str(e)[:120]}")
        return None


def _record_tokens(tokens: int, provider: str):
    try:
        from core.budget import budget
        budget.record(tokens, provider)
    except Exception:
        pass


class LLMRouter:
    def __init__(self):
        self._providers: list[ProviderConfig] = []
        self._cooldowns: dict[str, float] = {}
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
        return [p for p in self._providers if self._cooldowns.get(p.name, 0) < now]

    def _cooldown(self, name: str, seconds: float):
        self._cooldowns[name] = time.monotonic() + seconds
        logger.warning(f"{name} {seconds}s cooldown'a alindi")

    async def chat(self, messages: list[dict], max_tokens: int = 1024, heavy: bool = False) -> str:  # noqa: ARG002
        self._ensure_init()

        from core.budget import budget
        if budget.is_blocked():
            return "Gunluk token limitine ulasildi."

        for provider in self._available():
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
                    logger.debug(f"LLM: {provider.name} yanit verdi")
                    return result
                else:
                    self._cooldown(provider.name, 30)

            except Exception as e:
                err = str(e)
                seconds = 120 if "quota" in err.lower() else 60 if "429" in err else 30
                self._cooldown(provider.name, seconds)

        logger.error("LLM Router: Tum providerlar basarisiz")
        return "LLM yanit veremedi, lutfen tekrar deneyin."


router = LLMRouter()
