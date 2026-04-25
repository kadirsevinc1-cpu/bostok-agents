"""
Lead Scorer Skill — Lead potansiyelini puanlar, yüksek öncelikliyi öne alır.
LLM kullanmaz (0 token). Rating, website durumu, yorum sayısına göre sıralar.
"""
from dataclasses import dataclass
from loguru import logger


@dataclass
class ScoredLead:
    lead: object
    score: int
    reason: str


def score_lead(lead) -> ScoredLead:
    if not getattr(lead, "email", ""):
        return ScoredLead(lead=lead, score=0, reason="email yok")

    score = 50
    reasons: list[str] = []

    # Rating
    try:
        r = float(getattr(lead, "rating", 0) or 0)
        if r >= 4.5:
            score += 15
            reasons.append("yüksek rating")
        elif r >= 4.0:
            score += 8
        elif 0 < r < 3.5:
            score -= 10
            reasons.append("düşük rating")
    except (TypeError, ValueError):
        pass

    # Website yok = kolay satış
    has_site = getattr(lead, "has_website", True)
    if not has_site:
        score += 20
        reasons.append("website yok")
    else:
        score += 5  # sitesi var ama modernize edilebilir

    # Yorum sayısı — meşgul işletme = bütçe var
    try:
        reviews = int(getattr(lead, "review_count", 0) or 0)
        if reviews > 200:
            score += 15
            reasons.append("çok popüler")
        elif reviews > 100:
            score += 10
            reasons.append("aktif işletme")
        elif reviews > 50:
            score += 5
    except (TypeError, ValueError):
        pass

    return ScoredLead(
        lead=lead,
        score=min(score, 100),
        reason=", ".join(reasons) or "standart",
    )


def sort_leads_by_score(leads: list) -> list:
    """Leadleri puana göre sırala — en yüksek önce, emailsizleri at."""
    scored = [score_lead(lead) for lead in leads]
    scored.sort(key=lambda x: x.score, reverse=True)
    result = [s.lead for s in scored if s.score > 0]
    logger.debug(f"Lead skorlama: {len(result)}/{len(leads)} geçerli, "
                 f"en yüksek={scored[0].score if scored else 0} ({scored[0].reason if scored else '-'})")
    return result
