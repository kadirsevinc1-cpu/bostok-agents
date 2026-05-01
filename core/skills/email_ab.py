"""
Email A/B Subject Skill — 2 konu satırı üretip LLM ile daha iyisini seçer.
~100 token harcar. Açılma oranını artırmak için kullanılır.
"""
from loguru import logger

_LANG_NAMES = {"tr": "Turkish", "en": "English", "de": "German", "nl": "Dutch",
               "fr": "French", "es": "Spanish", "pt": "Portuguese", "it": "Italian",
               "pl": "Polish", "ar": "Arabic", "sv": "Swedish"}


async def pick_better_subject(lead_name: str, sector: str, lang: str, body_preview: str) -> str:
    """Returns the better of two generated subject lines. Returns empty string on error/timeout."""
    from core.llm_router import router

    lang_name = _LANG_NAMES.get(lang, "English")
    prompt = (
        f"Email in {lang_name} for the \"{lead_name}\" business ({sector} sector).\n"
        f"Email summary: {body_preview[:120]}\n\n"
        f"Write 2 different subject lines and select the one with the higher open rate.\n"
        "Reply only in this format (nothing else):\n"
        "SELECTED: [chosen subject line]"
    )
    messages = [
        {"role": "system", "content": "You are an email marketing expert. Give short, direct answers."},
        {"role": "user", "content": prompt},
    ]
    try:
        result = (await router.chat(messages, max_tokens=100)).strip()
        upper = result.upper()
        if "SELECTED:" in upper:
            idx = upper.find("SELECTED:")
            subject = result[idx + 9:].strip().split("\n")[0].strip()
            if 10 < len(subject) < 100:
                return subject
    except Exception as e:
        logger.warning(f"Email A/B error: {e}")
    return ""
