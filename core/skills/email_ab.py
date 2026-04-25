"""
Email A/B Subject Skill — 2 konu satırı üretip LLM ile daha iyisini seçer.
~100 token harcar. Açılma oranını artırmak için kullanılır.
"""
from loguru import logger

_LANG_NAMES = {"tr": "Türkçe", "en": "İngilizce", "de": "Almanca", "nl": "Flemenkçe", "fr": "Fransızca"}


async def pick_better_subject(lead_name: str, sector: str, lang: str, body_preview: str) -> str:
    """
    İki konu satırı alternatifi yaz ve hangisi daha iyi seçsin.
    Daha iyi konu satırını döndürür. Hata/timeout durumunda boş string döner.
    """
    from core.llm_router import router

    lang_name = _LANG_NAMES.get(lang, "İngilizce")
    prompt = (
        f"{sector} sektöründeki \"{lead_name}\" işletmesi için {lang_name} e-posta.\n"
        f"Mail özeti: {body_preview[:120]}\n\n"
        f"2 farklı konu satırı yaz ve açılma oranı daha yüksek olanı seç.\n"
        "Sadece şu formatta yanıt ver (başka hiçbir şey yazma):\n"
        "SECİLEN: [seçilen konu satırı]"
    )
    messages = [
        {"role": "system", "content": "Sen e-posta pazarlama uzmanısın. Kısa ve net yanıt verirsin."},
        {"role": "user", "content": prompt},
    ]
    try:
        result = (await router.chat(messages, max_tokens=100)).strip()
        marker = "SECİLEN:"
        upper = result.upper()
        if marker in upper or "SEC" in upper:
            idx = upper.find("SEC")
            after = result[idx:].split(":", 1)
            if len(after) > 1:
                subject = after[1].strip().split("\n")[0].strip()
                if 10 < len(subject) < 100:
                    return subject
    except Exception as e:
        logger.warning(f"Email A/B hatası: {e}")
    return ""
