import keyring
from pydantic_settings import BaseSettings
from pydantic import Field
from loguru import logger


class Settings(BaseSettings):
    # LLM Provider Keys (öncelik sırasına göre — ücretsizler önce, ücretliler sonda)
    groq_api_key:        str = Field("", env="GROQ_API_KEY")
    cerebras_api_key:    str = Field("", env="CEREBRAS_API_KEY")
    gemini_api_key:      str = Field("", env="GEMINI_API_KEY")
    mistral_api_key:     str = Field("", env="MISTRAL_API_KEY")
    sambanova_api_key:   str = Field("", env="SAMBANOVA_API_KEY")
    openrouter_api_key:  str = Field("", env="OPENROUTER_API_KEY")
    cohere_api_key:      str = Field("", env="COHERE_API_KEY")
    deepseek_api_key:    str = Field("", env="DEEPSEEK_API_KEY")
    anthropic_api_key:   str = Field("", env="ANTHROPIC_API_KEY")

    # Vercel deploy
    vercel_token:           str = Field("", env="VERCEL_TOKEN")

    # Netlify deploy
    netlify_token:          str = Field("", env="NETLIFY_TOKEN")
    netlify_demo_site_id:   str = Field("", env="NETLIFY_DEMO_SITE_ID")

    # Gmail (uygulama sifresi ile)
    gmail_user:          str = Field("", env="GMAIL_USER")
    gmail_app_password:  str = Field("", env="GMAIL_APP_PASSWORD")
    gmail_daily_limit:   int = Field(500, env="GMAIL_DAILY_LIMIT")

    # Google Maps Places API (lead finder icin - opsiyonel)
    google_maps_api_key: str = Field("", env="GOOGLE_MAPS_API_KEY")

    # Gorsel & Video
    pexels_api_key:      str = Field("", env="PEXELS_API_KEY")

    # Web Arama (tasarim ilham, opsiyonel)
    serpapi_api_key:     str = Field("", env="SERPAPI_API_KEY")
    serper_api_key:      str = Field("", env="SERPER_API_KEY")

    # WhatsApp (Green-API)
    greenapi_instance_id: str = Field("", env="GREENAPI_INSTANCE_ID")
    greenapi_api_token:   str = Field("", env="GREENAPI_API_TOKEN")

    # Telegram
    telegram_bot_token:  str = Field("", env="TELEGRAM_BOT_TOKEN")
    telegram_chat_id:    str = Field("", env="TELEGRAM_CHAT_ID")

    class Config:
        env_file = ".env"
        extra = "ignore"

    def model_post_init(self, __context):
        # .env'de yoksa Windows Credential Manager'dan al
        pairs = [
            ("groq_api_key",        "groq_api_key"),
            ("cerebras_api_key",    "cerebras_api_key"),
            ("gemini_api_key",      "gemini_api_key"),
            ("mistral_api_key",     "mistral_api_key"),
            ("sambanova_api_key",   "sambanova_api_key"),
            ("openrouter_api_key",  "openrouter_api_key"),
            ("cohere_api_key",      "cohere_api_key"),
            ("deepseek_api_key",    "deepseek_api_key"),
            ("anthropic_api_key",   "anthropic_api_key"),
            ("telegram_bot_token",  "telegram_bot_token"),
            ("netlify_token",        "netlify_token"),
            ("gmail_user",          "gmail_user"),
            ("gmail_app_password",  "gmail_app_password"),
            ("google_maps_api_key", "google_maps_api_key"),
            ("pexels_api_key",      "pexels_api_key"),
            ("serpapi_api_key",     "serpapi_api_key"),
            ("serper_api_key",      "serper_api_key"),
        ]
        for attr, key in pairs:
            if not getattr(self, attr):
                val = keyring.get_password("bostok_agents", key)
                if val:
                    object.__setattr__(self, attr, val)

        # Hangi key'ler aktif?
        active = [k for k, _ in pairs if getattr(self, k)]
        logger.info(f"Aktif API key'ler: {active}")


def save_key(key_name: str, value: str):
    """API key'i güvenli depola (Windows Credential Manager)."""
    keyring.set_password("bostok_agents", key_name, value)
    logger.info(f"Key kaydedildi: {key_name}")


settings = Settings()
