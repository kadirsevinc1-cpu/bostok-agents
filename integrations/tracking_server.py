"""Email açılma takibi + web dashboard — port 8080."""
import json
import os
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import Response, HTMLResponse
import uvicorn
from loguru import logger

OPENS_FILE  = Path("memory/email_opens.json")
UNSUB_FILE  = Path("memory/unsubscribed_via_link.json")

_PIXEL_GIF = bytes([
    0x47,0x49,0x46,0x38,0x39,0x61,0x01,0x00,0x01,0x00,
    0x80,0x00,0x00,0xff,0xff,0xff,0x00,0x00,0x00,0x21,
    0xf9,0x04,0x00,0x00,0x00,0x00,0x00,0x2c,0x00,0x00,
    0x00,0x00,0x01,0x00,0x01,0x00,0x00,0x02,0x02,0x44,
    0x01,0x00,0x3b,
])

_public_url = ""

app = FastAPI(docs_url=None, redoc_url=None)


def set_public_url(url: str):
    global _public_url
    _public_url = url.rstrip("/")
    logger.info(f"Tracking sunucusu: {_public_url}")


def get_tracking_url(msg_id: str) -> str:
    if not _public_url:
        return ""
    safe = msg_id.strip("<>").replace("/", "_").replace("+", "-")
    return f"{_public_url}/t/{safe}"


def get_unsub_url(msg_id: str) -> str:
    if not _public_url:
        return ""
    safe = msg_id.strip("<>").replace("/", "_").replace("+", "-")
    return f"{_public_url}/unsub/{safe}"


def _load_opens() -> dict:
    if OPENS_FILE.exists():
        try:
            return json.loads(OPENS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _record_open(safe_id: str, ip: str):
    OPENS_FILE.parent.mkdir(exist_ok=True)
    data = _load_opens()
    original = safe_id.replace("_", "/").replace("-", "+")
    key = f"<{original}>"

    existing = data.get(key, [])
    # Aynı IP'den 1 saatte bir say
    recent = [o for o in existing
              if o.get("ip") == ip and
              (datetime.now() - datetime.fromisoformat(o["ts"])).seconds < 3600]
    if recent:
        return

    existing.append({"ts": datetime.now().isoformat(), "ip": ip})
    data[key] = existing
    tmp = OPENS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, OPENS_FILE)
    logger.debug(f"Mail açıldı: {key} [{ip}]")

    try:
        _update_lead_open(key)
    except Exception:
        pass


def _update_lead_open(msg_id: str):
    sent_file = Path("memory/sent_message_ids.json")
    if not sent_file.exists():
        return
    sent = json.loads(sent_file.read_text(encoding="utf-8"))
    info = sent.get(msg_id, {})
    to_email = info.get("to", "")
    if not to_email:
        return
    from core.lead_state import get_tracker
    tracker = get_tracker()
    if tracker.get(to_email):
        tracker.add_event(to_email, "email_opened", f"Açıldı: {info.get('subject','')[:60]}")


@app.get("/t/{safe_id:path}")
async def tracking_pixel(safe_id: str, request: Request):
    ip = request.client.host if request.client else "unknown"
    _record_open(safe_id, ip)
    return Response(
        content=_PIXEL_GIF, media_type="image/gif",
        headers={"Cache-Control": "no-cache, no-store", "Pragma": "no-cache"},
    )


@app.get("/unsub/{safe_id:path}", response_class=HTMLResponse)
async def unsubscribe(safe_id: str):
    original = safe_id.replace("_", "/").replace("-", "+")
    key = f"<{original}>"
    email = ""

    sent_file = Path("memory/sent_message_ids.json")
    if sent_file.exists():
        try:
            sent = json.loads(sent_file.read_text(encoding="utf-8"))
            email = sent.get(key, {}).get("to", "")
        except Exception:
            pass

    if email:
        # Bounce listesine ekle — bir daha mail gitmez
        from integrations.gmail import record_bounce
        record_bounce(email)
        try:
            from core.lead_state import get_tracker, LeadStage
            get_tracker().update(email, LeadStage.UNSUBSCRIBED, "Unsubscribe link clicked")
        except Exception:
            pass
        # Log kaydet
        UNSUB_FILE.parent.mkdir(exist_ok=True)
        data: dict = {}
        if UNSUB_FILE.exists():
            try:
                data = json.loads(UNSUB_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        data[email] = datetime.now().isoformat()
        UNSUB_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"Unsubscribe: {email}")

    return """<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>body{font-family:Arial,sans-serif;display:flex;justify-content:center;align-items:center;
min-height:100vh;margin:0;background:#f8fafc}
.box{text-align:center;padding:40px;background:#fff;border-radius:12px;
box-shadow:0 2px 12px rgba(0,0,0,.08);max-width:400px}
h2{color:#1e293b;margin-bottom:12px}p{color:#64748b;font-size:14px}</style></head>
<body><div class="box">
<h2>✅ Unsubscribed</h2>
<p>You have been removed from our mailing list.<br>
You will not receive further emails from Bostok.dev.</p>
<p style="margin-top:20px;font-size:12px;color:#94a3b8">
Changed your mind? Reply to any of our previous emails.</p>
</div></body></html>"""


@app.get("/opens")
async def api_opens():
    return _load_opens()


@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    return _build_dashboard()


def _build_dashboard() -> str:
    sent_file = Path("memory/sent_emails.txt")
    sent_count = len(sent_file.read_text(encoding="utf-8").splitlines()) if sent_file.exists() else 0

    opens_data = _load_opens()
    open_count = sum(len(v) for v in opens_data.values())
    open_rate = f"{open_count / max(sent_count, 1) * 100:.1f}%"

    inbox_file = Path("memory/inbox_emails.json")
    reply_count = len(json.loads(inbox_file.read_text(encoding="utf-8"))) if inbox_file.exists() else 0
    reply_rate = f"{reply_count / max(sent_count, 1) * 100:.1f}%"

    bounce_file = Path("memory/bounced_emails.txt")
    bounce_count = len(bounce_file.read_text(encoding="utf-8").splitlines()) if bounce_file.exists() else 0

    from core.campaign_state import exhausted_count
    exhausted = exhausted_count()

    # Agent sağlık
    agent_rows = ""
    try:
        from agents.base import _AGENT_REGISTRY
        now = datetime.now()
        for name, agent in sorted(_AGENT_REGISTRY.items()):
            diff = (now - agent.last_heartbeat).total_seconds()
            color = "#22c55e" if diff < 120 else ("#f59e0b" if diff < 600 else "#ef4444")
            status = "Aktif" if diff < 120 else ("Yavaş" if diff < 600 else "Sessiz")
            lc = getattr(agent, "loop_count", 0)
            agent_rows += (
                f"<tr><td>{name}</td>"
                f"<td style='color:{color}'><b>{status}</b></td>"
                f"<td>{int(diff)}s önce</td>"
                f"<td>{lc:,}</td></tr>"
            )
    except Exception:
        agent_rows = "<tr><td colspan='4' style='color:#64748b'>Veri yok</td></tr>"

    # Lead pipeline
    stage_rows = ""
    try:
        from core.lead_state import get_tracker
        summary = get_tracker().summary()
        labels = {
            "new": "Yeni", "contacted": "Maillendi", "followed_up": "Takip 1",
            "followed_up2": "Takip 2", "replied": "Yanıtladı", "bounced": "Bounce",
            "unsubscribed": "İptal", "closed_won": "✅ Müşteri", "closed_lost": "Kapandı",
        }
        total = sum(summary.values())
        for stage, count in sorted(summary.items(), key=lambda x: -x[1]):
            pct = count / max(total, 1) * 100
            stage_rows += (
                f"<tr><td>{labels.get(stage, stage)}</td>"
                f"<td><b>{count}</b></td>"
                f"<td><div style='background:#3b82f6;height:8px;width:{pct:.0f}%;border-radius:4px;min-width:4px'></div></td>"
                f"<td style='color:#64748b'>{pct:.1f}%</td></tr>"
            )
    except Exception:
        stage_rows = "<tr><td colspan='4' style='color:#64748b'>Veri yok</td></tr>"

    # Son açılan mailler
    recent_rows = ""
    try:
        sent_ids_file = Path("memory/sent_message_ids.json")
        sent_ids = json.loads(sent_ids_file.read_text(encoding="utf-8")) if sent_ids_file.exists() else {}
        events = []
        for mid, opens_list in opens_data.items():
            info = sent_ids.get(mid, {})
            for o in opens_list:
                events.append((o["ts"], info.get("to", "?"), info.get("subject", "?")[:45], info.get("sector", "")))
        events.sort(reverse=True)
        for ts, to, subj, sector in events[:15]:
            recent_rows += (
                f"<tr><td style='color:#64748b'>{ts[:16]}</td>"
                f"<td>{to}</td><td>{subj}</td>"
                f"<td style='color:#94a3b8'>{sector}</td></tr>"
            )
    except Exception:
        recent_rows = "<tr><td colspan='4' style='color:#64748b'>Veri yok</td></tr>"

    # A/B istatistikleri
    ab_rows = ""
    try:
        from core.ab_tracker import get_top_patterns
        for p in get_top_patterns(8):
            ab_rows += (
                f"<tr><td>{p['subject'][:50]}</td>"
                f"<td style='color:#22c55e'><b>{p['replies']}</b></td>"
                f"<td>{p['sent']}</td>"
                f"<td style='color:#60a5fa'>{p['rate']:.1f}%</td></tr>"
            )
        if not ab_rows:
            ab_rows = "<tr><td colspan='4' style='color:#64748b'>Henüz yeterli veri yok</td></tr>"
    except Exception:
        ab_rows = "<tr><td colspan='4' style='color:#64748b'>Veri yok</td></tr>"

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return f"""<!DOCTYPE html>
<html lang="tr"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="30">
<title>Bostok Dashboard</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#0f172a;color:#e2e8f0;font-family:'Segoe UI',system-ui,sans-serif;padding:24px;font-size:14px}}
h1{{color:#60a5fa;font-size:22px;font-weight:700}}
.sub{{color:#475569;font-size:12px;margin:4px 0 24px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:16px;margin-bottom:24px}}
.card{{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:20px}}
.card .val{{font-size:32px;font-weight:800;color:#60a5fa;line-height:1}}
.card .sub2{{font-size:18px;color:#94a3b8;font-weight:600;margin-top:2px}}
.card .lbl{{font-size:12px;color:#64748b;margin-top:6px}}
.sec{{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:20px;margin-bottom:20px}}
.sec h2{{font-size:13px;font-weight:600;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em;margin-bottom:14px;padding-bottom:10px;border-bottom:1px solid #334155}}
table{{width:100%;border-collapse:collapse}}
th{{text-align:left;color:#475569;font-size:12px;padding:6px 10px;border-bottom:1px solid #334155;font-weight:600}}
td{{padding:8px 10px;border-bottom:1px solid #1a2744;vertical-align:middle}}
tr:last-child td{{border-bottom:none}}
tr:hover td{{background:rgba(255,255,255,.02)}}
</style></head>
<body>
<h1>🤖 Bostok Agent Köyü</h1>
<div class="sub">Son güncelleme: {now_str} &nbsp;·&nbsp; Otomatik yenileme: 30s &nbsp;·&nbsp; Kampanya: 201 kombinasyon, {exhausted} tükendi</div>

<div class="grid">
  <div class="card">
    <div class="val">{sent_count:,}</div>
    <div class="lbl">📧 Gönderilen Mail</div>
  </div>
  <div class="card">
    <div class="val">{open_count:,}</div>
    <div class="sub2">{open_rate}</div>
    <div class="lbl">👁️ Açılan (açılma oranı)</div>
  </div>
  <div class="card">
    <div class="val">{reply_count:,}</div>
    <div class="sub2">{reply_rate}</div>
    <div class="lbl">💬 Yanıt (yanıt oranı)</div>
  </div>
  <div class="card">
    <div class="val">{bounce_count:,}</div>
    <div class="lbl">❌ Bounce (geçersiz)</div>
  </div>
</div>

<div class="sec"><h2>⚡ Agent Sağlık Durumu</h2>
<table>
<thead><tr><th>Agent</th><th>Durum</th><th>Son Aktivite</th><th>Loop Sayısı</th></tr></thead>
<tbody>{agent_rows}</tbody>
</table></div>

<div class="sec"><h2>📊 Lead Pipeline</h2>
<table>
<thead><tr><th>Aşama</th><th>Adet</th><th>Dağılım</th><th>%</th></tr></thead>
<tbody>{stage_rows}</tbody>
</table></div>

<div class="sec"><h2>🏆 En İyi Konu Satırları (A/B)</h2>
<table>
<thead><tr><th>Konu</th><th>Yanıt</th><th>Gönderim</th><th>Oran</th></tr></thead>
<tbody>{ab_rows}</tbody>
</table></div>

<div class="sec"><h2>👁️ Son Açılan Mailler</h2>
<table>
<thead><tr><th>Zaman</th><th>Alıcı</th><th>Konu</th><th>Sektör</th></tr></thead>
<tbody>{recent_rows}</tbody>
</table></div>

</body></html>"""


async def start(port: int = 8080):
    config = uvicorn.Config(app, host="0.0.0.0", port=port,
                            log_level="warning", access_log=False)
    server = uvicorn.Server(config)
    await server.serve()
