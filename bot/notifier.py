import logging
import time
import requests
from config import BOT_TOKEN, CHAT_ID
from bot.parser import VPNConfig

logger = logging.getLogger(__name__)

API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"
DIV      = "▬" * 18

# ─── Per-Protocol Styling ─────────────────────────────────────────────────────

PROTO_HEADER = {
    "VLESS":       "⚡  V L E S S",
    "VMess":       "🔮  V M E S S",
    "Trojan":      "🐴  T R O J A N",
    "Hysteria2":   "🚀  H Y S T E R I A  2",
    "Shadowsocks": "🌑  S H A D O W S O C K S",
    "TUIC":        "🌊  T U I C",
}

PROTO_TAG = {
    "VLESS":       "#VLESS #Reality",
    "VMess":       "#VMess #V2Ray",
    "Trojan":      "#Trojan",
    "Hysteria2":   "#Hysteria2 #Hy2",
    "Shadowsocks": "#Shadowsocks #SS",
    "TUIC":        "#TUIC",
}


# ─── HTTP Helper ──────────────────────────────────────────────────────────────

def _post(method: str, **kwargs) -> dict:
    resp = requests.post(f"{API_BASE}/{method}", timeout=15, **kwargs)
    if not resp.ok:
        try:
            detail = resp.json().get("description", resp.text[:200])
        except Exception:
            detail = resp.text[:200]
        raise requests.HTTPError(f"{resp.status_code} {detail}", response=resp)
    return resp.json()


# ─── Caption Builder ──────────────────────────────────────────────────────────

def _build_message(cfg: VPNConfig) -> str:
    header = PROTO_HEADER.get(cfg.protocol, f"🔒  {cfg.protocol.upper()}")
    tags   = PROTO_TAG.get(cfg.protocol, "#VPN")

    # Extra protocol detail lines
    extras = ""
    if cfg.protocol == "VLESS":
        sec  = cfg.extra.get("security", "none")
        net  = cfg.extra.get("network", "tcp")
        flow = cfg.extra.get("flow", "")
        extras += f"🔐  <b>Security:</b>  <code>{sec}</code>\n"
        extras += f"📡  <b>Network:</b>  <code>{net}</code>\n"
        if flow:
            extras += f"💨  <b>Flow:</b>  <code>{flow}</code>\n"
    elif cfg.protocol == "VMess":
        net = cfg.extra.get("net", "tcp")
        tls = cfg.extra.get("tls", "")
        extras += f"📡  <b>Network:</b>  <code>{net}</code>\n"
        if tls:
            extras += f"🔐  <b>TLS:</b>  <code>{tls}</code>\n"
    elif cfg.protocol in ("Trojan", "Hysteria2"):
        sni = cfg.extra.get("sni", "")
        if sni:
            extras += f"🔐  <b>SNI:</b>  <code>{sni}</code>\n"

    # Truncate config if over 3600 chars (Telegram limit is 4096 total)
    raw = cfg.raw if len(cfg.raw) <= 3500 else cfg.raw[:3497] + "..."

    return (
        f"{DIV}\n"
        f"<b>{header}</b>\n"
        f"{DIV}\n"
        f"\n"
        f"🌍  <b>Location:</b>  {cfg.country}\n"
        f"🖥  <b>Server:</b>  <code>{cfg.host}</code>\n"
        f"🔌  <b>Port:</b>  <b>{cfg.port}</b>\n"
        f"{extras}"
        f"\n"
        f"📋  <b>Config</b>  <i>(tap to copy)</i>:\n"
        f"<code>{raw}</code>\n"
        f"\n"
        f"<i>{tags} #FreeVPN #FreeConfig #VPN #Proxy</i>"
    )


# ─── Send ─────────────────────────────────────────────────────────────────────

def send_config(cfg: VPNConfig) -> bool:
    text = _build_message(cfg)

    # Telegram text message limit = 4096 chars
    if len(text) > 4096:
        text = text[:4090] + "…</i>"

    try:
        _post("sendMessage", data={
            "chat_id":                  CHAT_ID,
            "text":                     text,
            "parse_mode":               "HTML",
            "disable_web_page_preview": True,
        })
        logger.info(f"Sent: [{cfg.protocol}] {cfg.country} | {cfg.host}:{cfg.port}")
        time.sleep(1.5)   # avoid Telegram flood
        return True
    except Exception as e:
        logger.error(f"Failed to send [{cfg.protocol}] {cfg.host}: {e}")
        return False


def send_status(text: str) -> None:
    try:
        _post("sendMessage", data={
            "chat_id":    CHAT_ID,
            "text":       text,
            "parse_mode": "HTML",
        })
    except Exception as e:
        logger.error(f"Failed to send status: {e}")
