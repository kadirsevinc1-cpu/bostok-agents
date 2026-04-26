"""Kullanıcı profili — ajan iradesini temsil eden tercih ve kural seti."""
import json
from functools import lru_cache
from pathlib import Path

_PROFILE_PATH = Path(__file__).parent.parent / "memory" / "user_profile.json"


def get_profile() -> dict:
    if not _PROFILE_PATH.exists():
        return {}
    try:
        return json.loads(_PROFILE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_profile(profile: dict) -> None:
    _PROFILE_PATH.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_context(for_agent: str = "") -> str:
    """Agent system prompt'una enjekte edilecek kullanıcı profil özeti."""
    p = get_profile()
    if not p:
        return ""

    owner = p.get("owner", {})
    tone = p.get("tone", {})
    sectors = p.get("sectors", {})
    campaign = p.get("campaign", {})
    notes = p.get("notes", "")

    high = ", ".join(sectors.get("high_priority", []))
    avoid = ", ".join(f'"{x}"' for x in tone.get("avoid", []))
    langs = ", ".join(campaign.get("default_languages", ["tr"]))

    lines = [
        f"[Kullanıcı Profili — {owner.get('name', '')} / {owner.get('agency', '')}]",
        f"İmza: {owner.get('signature', '').split(chr(10))[0]}",
        f"Ton: {tone.get('style', '')} — max {tone.get('max_words_per_mail', 130)} kelime",
        f"Kaçın: {avoid}",
        f"Öncelikli sektörler: {high}",
        f"Varsayılan diller: {langs}",
    ]
    if notes:
        lines.append(f"Bağlam: {notes}")

    return "\n".join(lines)


def high_priority_sectors() -> list[str]:
    return get_profile().get("sectors", {}).get("high_priority", [])


def default_languages() -> list[str]:
    return get_profile().get("campaign", {}).get("default_languages", ["tr", "en"])


def auto_approve_threshold() -> int:
    return get_profile().get("approval", {}).get("auto_approve_campaigns_under_n_leads", 20)


def focus_cities() -> list[str]:
    return get_profile().get("focus_cities", [])


def format_profile_summary() -> str:
    """Telegram /profil komutu için okunabilir özet."""
    p = get_profile()
    if not p:
        return "Profil bulunamadı."

    owner = p.get("owner", {})
    campaign = p.get("campaign", {})
    sectors = p.get("sectors", {})
    approval = p.get("approval", {})
    cities = p.get("focus_cities", [])

    high = ", ".join(sectors.get("high_priority", []))
    mid = ", ".join(sectors.get("medium_priority", []))
    langs = ", ".join(campaign.get("default_languages", []))
    top_cities = ", ".join(cities[:5])

    return (
        f"<b>👤 Kullanıcı Profili</b>\n\n"
        f"<b>Ajans:</b> {owner.get('agency', '')} — {owner.get('agency_url', '')}\n"
        f"<b>Yetkili:</b> {owner.get('name', '')}\n\n"
        f"<b>📋 Kampanya Tercihleri</b>\n"
        f"Diller: {langs}\n"
        f"Günlük limit: {campaign.get('daily_mail_limit', '?')} mail\n"
        f"Takip: {campaign.get('followup_after_days', '?')} günde bir, max {campaign.get('max_followups_per_lead', '?')} kez\n\n"
        f"<b>🎯 Sektör Öncelikleri</b>\n"
        f"Yüksek: {high}\n"
        f"Orta: {mid}\n\n"
        f"<b>🏙️ Odak Şehirler</b>\n{top_cities}...\n\n"
        f"<b>⚙️ Otomatik Onay</b>\n"
        f"≤{approval.get('auto_approve_campaigns_under_n_leads', '?')} lead: otomatik başlat\n"
        f"Her yanıtta bildir: {'✅' if approval.get('notify_on_every_reply') else '❌'}"
    )
