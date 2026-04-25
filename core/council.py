"""
Proje Konseyi — brief onaylanmadan pipeline başlamaz.
3 uzman paralel oy kullanır (max 150 tok/üye → ~500 tok toplam).
2/3 ONAY → pipeline devam eder. 2/3 RET → kullanıcıya bildirim, pipeline durur.
"""
import asyncio
from dataclasses import dataclass, field
from loguru import logger

BRIEF_SNIPPET_LEN = 600  # token tasarrufu: brief'in ilk N karakteri yeterli


@dataclass
class Vote:
    member: str
    approved: bool
    note: str


@dataclass
class CouncilDecision:
    approved: bool
    votes: list[Vote] = field(default_factory=list)

    def report(self) -> str:
        lines = "\n".join(
            f"{'✅' if v.approved else '❌'} {v.member}: {v.note}"
            for v in self.votes
        )
        approval_count = sum(1 for v in self.votes if v.approved)
        status = "ONAYLANDI ✅" if self.approved else "REDDEDİLDİ ❌"
        return (
            f"Konsey Toplantısı Sonucu: {status} ({approval_count}/{len(self.votes)} oy)\n\n"
            f"{lines}\n\n"
            + ("Pipeline başlatılıyor." if self.approved else
               "Pipeline durduruldu. Talebi revize edip tekrar gönderin.")
        )


_MEMBERS = [
    {
        "name": "Kapsam Uzmanı",
        "system": (
            "Sen bir web ajansının kapsam ve gereksinim uzmanısın. "
            "Proje brieflerini hızlı ve net değerlendirirsin. Tek satırda yanıt verirsin."
        ),
        "question": (
            "Proje brief özeti:\n{brief}\n\n"
            "Kapsam açık mı? Kritik eksik bilgi var mı? Devam edilebilir mi?\n"
            "Yanıt (sadece bu format, tek satır): ONAY: [kısa gerekçe] VEYA RET: [kısa gerekçe]"
        ),
    },
    {
        "name": "Fizibilite Uzmanı",
        "system": (
            "Sen bir web ajansının bütçe ve fizibilite uzmanısın. "
            "Projelerin süre ve teknik uygunluğunu değerlendirirsin. Tek satırda yanıt verirsin."
        ),
        "question": (
            "Proje brief özeti:\n{brief}\n\n"
            "Süre ve kapsam makul mu? Teknik zorluk kabul edilebilir mi?\n"
            "Yanıt (sadece bu format, tek satır): ONAY: [kısa gerekçe] VEYA RET: [kısa gerekçe]"
        ),
    },
    {
        "name": "Kalite & Risk Uzmanı",
        "system": (
            "Sen bir web ajansının kalite kontrol ve risk uzmanısın. "
            "Projelerin risklerini ve belirsizliklerini tespit edersin. Tek satırda yanıt verirsin."
        ),
        "question": (
            "Proje brief özeti:\n{brief}\n\n"
            "Üretim riskler? Belirsiz gereksinimler? Pipeline'ı durduracak kritik eksik var mı?\n"
            "Yanıt (sadece bu format, tek satır): ONAY: [kısa gerekçe] VEYA RET: [kısa gerekçe]"
        ),
    },
]


async def _ask_member(member: dict, brief_snippet: str) -> Vote:
    from core.llm_router import router
    messages = [
        {"role": "system", "content": member["system"]},
        {"role": "user", "content": member["question"].format(brief=brief_snippet)},
    ]
    try:
        result = (await router.chat(messages, max_tokens=150)).strip()
        upper = result.upper()
        approved = upper.startswith("ONAY")
        note = result.split(":", 1)[1].strip() if ":" in result else result
        return Vote(member=member["name"], approved=approved, note=note[:120])
    except Exception as e:
        logger.warning(f"Konsey uye hatasi [{member['name']}]: {e}")
        return Vote(member=member["name"], approved=True, note="Degerlendirilemedi, varsayilan onay.")


async def hold_meeting(brief: str) -> CouncilDecision:
    """Brief'i 3 uzmana paralel gönder, 2/3 oy ile karar ver."""
    snippet = brief[:BRIEF_SNIPPET_LEN]
    logger.info("Konsey toplantisi basladi (3 paralel oy)...")

    try:
        votes = list(
            await asyncio.wait_for(
                asyncio.gather(*[_ask_member(m, snippet) for m in _MEMBERS]),
                timeout=45.0,
            )
        )
    except asyncio.TimeoutError:
        logger.warning("Konsey zaman asimi (45s) — varsayilan ONAY verildi")
        votes = [Vote(m["name"], True, "Zaman asimi — varsayilan onay") for m in _MEMBERS]

    approval_count = sum(1 for v in votes if v.approved)
    approved = approval_count >= 2

    logger.info(
        f"Konsey karari: {approval_count}/3 ONAY → {'ONAYLANDI' if approved else 'REDDEDİLDİ'}"
    )
    return CouncilDecision(approved=approved, votes=votes)
