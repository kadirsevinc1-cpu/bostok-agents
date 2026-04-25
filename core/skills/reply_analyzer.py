"""Gelen e-posta yaniti analizi — keyword tabanlı hızlı tespit (0 token) + isteğe bağlı LLM."""
from dataclasses import dataclass
from enum import Enum


class ReplyIntent(str, Enum):
    INTERESTED      = "interested"       # ilgili, fiyat/bilgi soruyor
    MEETING         = "meeting"          # toplanti/gorusme istiyor
    READY_TO_BUY    = "ready"            # satin almaya hazir
    UNSUBSCRIBE     = "unsubscribe"      # listeden cikmak istiyor
    NEGATIVE        = "negative"         # olumsuz, ilgisiz
    QUESTION        = "question"         # spesifik soru soruyor
    SPAM            = "spam"             # otomatik yanit / spam
    UNKNOWN         = "unknown"


@dataclass
class ReplyAnalysis:
    intent: ReplyIntent
    confidence: float          # 0.0 – 1.0
    summary: str
    suggested_action: str
    priority: int              # 1 (acil) – 3 (dusuk)


_KEYWORDS: dict[ReplyIntent, list[str]] = {
    ReplyIntent.UNSUBSCRIBE: [
        "unsubscribe", "abonelik", "listeden cikar", "istemiyorum", "durdurun",
        "remove me", "opt out", "listeye ekleme", "bana gonderme",
    ],
    ReplyIntent.NEGATIVE: [
        "hayir", "ilgilenmiyorum", "gerek yok", "no thanks", "not interested",
        "kein interesse", "pas interesse", "ilgim yok", "ihtiyacimiz yok",
    ],
    ReplyIntent.SPAM: [
        "noreply", "no-reply", "auto-reply", "otomatik yanit", "tatildeyim",
        "out of office", "vacation", "mailer-daemon", "postmaster",
    ],
    ReplyIntent.MEETING: [
        "toplanti", "gorusme", "randevu", "meeting", "call", "teams", "zoom",
        "konusalim", "arayabilir misiniz", "goruselim",
    ],
    ReplyIntent.READY_TO_BUY: [
        "ne zaman baslariz", "sozlesme", "odeme", "fatura", "siparis",
        "nasil ilerleriz", "proceed", "contract", "invoice", "anlasmaya hazir",
        "ne zaman baslayabilirsiniz",
    ],
    ReplyIntent.INTERESTED: [
        "fiyat", "ucret", "ne kadar", "teklif", "bilgi", "detay", "portfolio",
        "ornekler", "referans", "price", "cost", "quote", "interested",
        "more info", "daha fazla bilgi", "site ornegi",
    ],
    ReplyIntent.QUESTION: [
        "nasil", "ne kadar sure", "hangi teknoloji", "destek", "bakim",
        "domain", "hosting", "ne zaman", "kimlerle", "how long",
    ],
}

_ACTIONS: dict[ReplyIntent, str] = {
    ReplyIntent.INTERESTED:   "Kisa surede teklif gonder, portfolyo linkini ekle",
    ReplyIntent.MEETING:      "Hemen yanit yaz, Calendly/WhatsApp baglantisi ver",
    ReplyIntent.READY_TO_BUY: "ACIL: Sozlesme taslagi hazirla, 1 saat icinde yanıtla",
    ReplyIntent.UNSUBSCRIBE:  "Listeden cikar, bir daha mail gonderme",
    ReplyIntent.NEGATIVE:     "Kibarca kabul et, listeye NOT ekle",
    ReplyIntent.QUESTION:     "Soruyu yanitla, demo/ornek ekle",
    ReplyIntent.SPAM:         "Yoksay",
    ReplyIntent.UNKNOWN:      "LLM ile derin analiz yap",
}

_PRIORITY: dict[ReplyIntent, int] = {
    ReplyIntent.READY_TO_BUY: 1,
    ReplyIntent.MEETING:      1,
    ReplyIntent.INTERESTED:   2,
    ReplyIntent.QUESTION:     2,
    ReplyIntent.NEGATIVE:     3,
    ReplyIntent.UNSUBSCRIBE:  3,
    ReplyIntent.SPAM:         3,
    ReplyIntent.UNKNOWN:      2,
}


def analyze_reply(body: str, subject: str = "") -> ReplyAnalysis:
    """Keyword tabanlı hizli analiz, 0 token kullanir."""
    text = (subject + " " + body).lower()

    scores: dict[ReplyIntent, int] = {i: 0 for i in ReplyIntent}
    for intent, keywords in _KEYWORDS.items():
        scores[intent] = sum(1 for kw in keywords if kw in text)

    # Spam oncelikli kontrol (otomatik yanitlar karmasiklik olusturur)
    if scores[ReplyIntent.SPAM] > 0:
        return ReplyAnalysis(
            intent=ReplyIntent.SPAM,
            confidence=0.95,
            summary="Otomatik/spam yanit tespit edildi",
            suggested_action=_ACTIONS[ReplyIntent.SPAM],
            priority=_PRIORITY[ReplyIntent.SPAM],
        )

    best = max(scores, key=lambda i: scores[i])
    best_score = scores[best]

    if best_score == 0:
        best = ReplyIntent.QUESTION if "?" in body else ReplyIntent.UNKNOWN
        confidence = 0.4
    else:
        total = sum(scores.values())
        confidence = round(min(best_score / max(total, 1), 1.0), 2)

    return ReplyAnalysis(
        intent=best,
        confidence=confidence,
        summary=f"Tespit: {best.value} (guven: {confidence:.0%})",
        suggested_action=_ACTIONS[best],
        priority=_PRIORITY[best],
    )


async def analyze_reply_with_llm(body: str, subject: str = "") -> ReplyAnalysis:
    """Guven dusukse LLM ile derinlestirir (~80 token)."""
    fast = analyze_reply(body, subject)
    if fast.confidence >= 0.6:
        return fast

    from core.llm_router import router
    snippet = (subject + "\n" + body)[:400]
    prompt = (
        f"Bu e-posta yanitinin amacini tek kelimeyle belirle:\n\n{snippet}\n\n"
        "Secenekler: interested / meeting / ready / unsubscribe / negative / question / spam / unknown\n"
        "Sadece kelimeyi yaz."
    )
    try:
        raw = (await router.chat(
            [{"role": "user", "content": prompt}], max_tokens=10
        )).strip().lower()
        try:
            intent = ReplyIntent(raw)
        except ValueError:
            intent = ReplyIntent.UNKNOWN
    except Exception:
        intent = ReplyIntent.UNKNOWN

    return ReplyAnalysis(
        intent=intent,
        confidence=0.75,
        summary=f"LLM tespiti: {intent.value}",
        suggested_action=_ACTIONS[intent],
        priority=_PRIORITY[intent],
    )
