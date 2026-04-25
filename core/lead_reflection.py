"""Lead reflection — 5+ event sonrası lead davranış pattern'ini sentezle."""
from datetime import datetime
from loguru import logger

REFLECTION_EVENT_THRESHOLD = 5
REFLECTION_COOLDOWN_HOURS = 24

_last_reflection: dict[str, datetime] = {}


async def maybe_reflect(email: str) -> str | None:
    """Lead için yeterli veri varsa LLM ile insight üret, hafızaya kaydet."""
    from core.lead_state import get_tracker
    rec = get_tracker().get(email)
    if not rec or len(rec.events) < REFLECTION_EVENT_THRESHOLD:
        return None

    last = _last_reflection.get(email)
    if last and (datetime.now() - last).total_seconds() < REFLECTION_COOLDOWN_HOURS * 3600:
        return None

    events_text = "\n".join(
        f"- [{e['ts'][:10]}] {e['type']}: {e['note']}"
        for e in rec.events[-10:]
    )
    prompt = (
        f"Lead: {rec.name or email}, Sektör: {rec.sector}, Konum: {rec.location}\n"
        f"Mevcut aşama: {rec.stage}\n\n"
        f"Son eventler:\n{events_text}\n\n"
        "Bu lead hakkında 1-2 cümlelik içgörü yaz: neden bu aşamada, "
        "bir sonraki mail için ne önerilir? Sadece içgörüyü yaz."
    )
    try:
        from core.llm_router import router
        insight = await router.chat([
            {"role": "system", "content": "B2B satış danışmanısın. Kısa ve net içgörüler üretirsin."},
            {"role": "user", "content": prompt},
        ], max_tokens=150)

        if insight and len(insight.strip()) > 20:
            from core.memory import store
            store.add(
                f"Lead insight [{rec.name}/{rec.sector}]: {insight[:300]}",
                "FollowupAgent",
                "lead_insight",
                importance=8.5,
            )
            _last_reflection[email] = datetime.now()
            logger.info(f"Lead reflection üretildi: {email}")
            return insight
    except Exception as e:
        logger.debug(f"Lead reflection hata [{email}]: {e}")
    return None


async def get_insight(email: str) -> str:
    """Lead için hafızadan mevcut insight'ı getir."""
    from core.lead_state import get_tracker
    from core.memory import store
    rec = get_tracker().get(email)
    if not rec:
        return ""
    query = f"Lead insight {rec.name} {rec.sector}"
    mems = store.retrieve(query, "FollowupAgent", n=5)
    for m in mems:
        if m.type == "lead_insight" and (rec.name in m.content or rec.sector in m.content):
            return m.content[:300]
    return ""
