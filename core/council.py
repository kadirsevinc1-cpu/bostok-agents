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
        "name": "Scope Expert",
        "system": (
            "You are the scope and requirements expert of a web agency. "
            "You evaluate project briefs quickly and clearly. Reply in a single line."
        ),
        "question": (
            "Project brief summary:\n{brief}\n\n"
            "Is the scope clear? Any critical missing information? Can we proceed?\n"
            "Reply (this format only, single line): APPROVE: [short reason] OR REJECT: [short reason]"
        ),
    },
    {
        "name": "Feasibility Expert",
        "system": (
            "You are the budget and feasibility expert of a web agency. "
            "You assess project timelines and technical suitability. Reply in a single line."
        ),
        "question": (
            "Project brief summary:\n{brief}\n\n"
            "Are the timeline and scope reasonable? Is the technical complexity acceptable?\n"
            "Reply (this format only, single line): APPROVE: [short reason] OR REJECT: [short reason]"
        ),
    },
    {
        "name": "Quality & Risk Expert",
        "system": (
            "You are the quality control and risk expert of a web agency. "
            "You identify risks and ambiguities in projects. Reply in a single line."
        ),
        "question": (
            "Project brief summary:\n{brief}\n\n"
            "Production risks? Ambiguous requirements? Any critical gaps that should stop the pipeline?\n"
            "Reply (this format only, single line): APPROVE: [short reason] OR REJECT: [short reason]"
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
        approved = upper.startswith("APPROVE")
        note = result.split(":", 1)[1].strip() if ":" in result else result
        return Vote(member=member["name"], approved=approved, note=note[:120])
    except Exception as e:
        logger.warning(f"Council member error [{member['name']}]: {e}")
        return Vote(member=member["name"], approved=True, note="Could not evaluate, default approval.")


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
