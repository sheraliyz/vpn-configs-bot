import base64
import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse, parse_qs, unquote

# ─── Data Model ───────────────────────────────────────────────────────────────

@dataclass
class VPNConfig:
    id:       str          # 16-char SHA256 of raw string (dedup key)
    raw:      str          # Full original config URI
    protocol: str          # VLESS / VMess / Trojan / Hysteria2 / Shadowsocks / TUIC
    host:     str          # Server hostname / IP
    port:     int          # Server port
    name:     str          # Remark / display name from config
    country:  str          # Country flag + name (guessed from name/host)
    extra:    dict = field(default_factory=dict)


# ─── Country Detection ────────────────────────────────────────────────────────

_COUNTRY_PATTERNS = [
    (r"\bUS\b|United.?States|\busa\b|United States",         "🇺🇸 USA"),
    (r"\bDE\b|German",                                        "🇩🇪 Germany"),
    (r"\bNL\b|Netherlands|Holland",                           "🇳🇱 Netherlands"),
    (r"\bFR\b|France",                                        "🇫🇷 France"),
    (r"\bGB\b|United.?Kingdom|Britain|\buk\b",                "🇬🇧 UK"),
    (r"\bCA\b|Canada",                                        "🇨🇦 Canada"),
    (r"\bSG\b|Singapore",                                     "🇸🇬 Singapore"),
    (r"\bJP\b|Japan",                                         "🇯🇵 Japan"),
    (r"\bKR\b|Korea",                                         "🇰🇷 South Korea"),
    (r"\bTR\b|Turkey|Türk",                                   "🇹🇷 Turkey"),
    (r"\bRU\b|Russia",                                        "🇷🇺 Russia"),
    (r"\bAU\b|Australia",                                     "🇦🇺 Australia"),
    (r"\bFI\b|Finland",                                       "🇫🇮 Finland"),
    (r"\bSE\b|Sweden",                                        "🇸🇪 Sweden"),
    (r"\bNO\b|Norway",                                        "🇳🇴 Norway"),
    (r"\bCH\b|Swiss",                                         "🇨🇭 Switzerland"),
    (r"\bHK\b|Hong.?Kong",                                    "🇭🇰 Hong Kong"),
    (r"\bTW\b|Taiwan",                                        "🇹🇼 Taiwan"),
    (r"\bIN\b|India",                                         "🇮🇳 India"),
    (r"\bBR\b|Brazil",                                        "🇧🇷 Brazil"),
    (r"\bPL\b|Poland",                                        "🇵🇱 Poland"),
    (r"\bCZ\b|Czech",                                         "🇨🇿 Czechia"),
    (r"\bAT\b|Austria",                                       "🇦🇹 Austria"),
    (r"\bLU\b|Luxembourg",                                    "🇱🇺 Luxembourg"),
    (r"\bIR\b|Iran",                                          "🇮🇷 Iran"),
    (r"\bUZ\b|Uzbek",                                         "🇺🇿 Uzbekistan"),
    (r"\bAZ\b|Azerbai",                                       "🇦🇿 Azerbaijan"),
    (r"\bKZ\b|Kazakh",                                        "🇰🇿 Kazakhstan"),
    (r"\bUA\b|Ukraine",                                       "🇺🇦 Ukraine"),
    (r"\bRO\b|Romania",                                       "🇷🇴 Romania"),
    (r"\bHU\b|Hungary",                                       "🇭🇺 Hungary"),
    (r"\bIT\b|Italy|Italia",                                   "🇮🇹 Italy"),
    (r"\bES\b|Spain|España",                                  "🇪🇸 Spain"),
    (r"\bCN\b|China|\bcn\b",                                  "🇨🇳 China"),
    (r"\bMY\b|Malaysia",                                      "🇲🇾 Malaysia"),
    (r"\bTH\b|Thailand",                                      "🇹🇭 Thailand"),
    (r"\bVN\b|Vietnam",                                       "🇻🇳 Vietnam"),
    (r"\bID\b|Indonesia",                                     "🇮🇩 Indonesia"),
]


def _detect_country(text: str) -> str:
    for pattern, country in _COUNTRY_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return country
    return "🌐 Unknown"


def _config_id(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ─── Protocol Parsers ─────────────────────────────────────────────────────────

def _parse_vless(raw: str) -> Optional[VPNConfig]:
    try:
        p = urlparse(raw)
        host    = p.hostname or "?"
        port    = p.port or 443
        name    = unquote(p.fragment) if p.fragment else host
        params  = parse_qs(p.query)
        security = params.get("security", ["none"])[0]
        network  = params.get("type", ["tcp"])[0]
        flow     = params.get("flow", [""])[0]
        sni      = params.get("sni", [""])[0]
        country  = _detect_country(name + " " + host + " " + sni)
        return VPNConfig(
            id=_config_id(raw), raw=raw, protocol="VLESS",
            host=host, port=port, name=name, country=country,
            extra={"security": security, "network": network, "flow": flow}
        )
    except Exception:
        return None


def _parse_vmess(raw: str) -> Optional[VPNConfig]:
    try:
        b64 = raw[len("vmess://"):]
        padded = b64 + "=" * (4 - len(b64) % 4)
        data   = json.loads(base64.b64decode(padded).decode("utf-8", errors="ignore"))
        host   = data.get("add", "?")
        port   = int(data.get("port", 443))
        name   = data.get("ps") or host
        country = _detect_country(name + " " + host)
        return VPNConfig(
            id=_config_id(raw), raw=raw, protocol="VMess",
            host=host, port=port, name=name, country=country,
            extra={"net": data.get("net", "tcp"), "tls": data.get("tls", "")}
        )
    except Exception:
        return None


def _parse_trojan(raw: str) -> Optional[VPNConfig]:
    try:
        p    = urlparse(raw)
        host = p.hostname or "?"
        port = p.port or 443
        name = unquote(p.fragment) if p.fragment else host
        params = parse_qs(p.query)
        sni  = params.get("sni", [""])[0]
        country = _detect_country(name + " " + host + " " + sni)
        return VPNConfig(
            id=_config_id(raw), raw=raw, protocol="Trojan",
            host=host, port=port, name=name, country=country,
            extra={"sni": sni}
        )
    except Exception:
        return None


def _parse_hysteria2(raw: str) -> Optional[VPNConfig]:
    try:
        p    = urlparse(raw)
        host = p.hostname or "?"
        port = p.port or 443
        name = unquote(p.fragment) if p.fragment else host
        params = parse_qs(p.query)
        sni  = params.get("sni", [""])[0]
        country = _detect_country(name + " " + host + " " + sni)
        return VPNConfig(
            id=_config_id(raw), raw=raw, protocol="Hysteria2",
            host=host, port=port, name=name, country=country,
            extra={"sni": sni, "obfs": params.get("obfs", ["none"])[0]}
        )
    except Exception:
        return None


def _parse_ss(raw: str) -> Optional[VPNConfig]:
    try:
        p    = urlparse(raw)
        host = p.hostname or "?"
        port = p.port or 8388
        name = unquote(p.fragment) if p.fragment else host
        country = _detect_country(name + " " + host)
        return VPNConfig(
            id=_config_id(raw), raw=raw, protocol="Shadowsocks",
            host=host, port=port, name=name, country=country,
        )
    except Exception:
        return None


def _parse_tuic(raw: str) -> Optional[VPNConfig]:
    try:
        p    = urlparse(raw)
        host = p.hostname or "?"
        port = p.port or 443
        name = unquote(p.fragment) if p.fragment else host
        country = _detect_country(name + " " + host)
        return VPNConfig(
            id=_config_id(raw), raw=raw, protocol="TUIC",
            host=host, port=port, name=name, country=country,
        )
    except Exception:
        return None


# ─── Public API ───────────────────────────────────────────────────────────────

def parse_config(raw: str) -> Optional[VPNConfig]:
    raw = raw.strip()
    if raw.startswith("vless://"):
        return _parse_vless(raw)
    if raw.startswith("vmess://"):
        return _parse_vmess(raw)
    if raw.startswith("trojan://"):
        return _parse_trojan(raw)
    if raw.startswith(("hysteria2://", "hy2://")):
        return _parse_hysteria2(raw)
    if raw.startswith("ss://"):
        return _parse_ss(raw)
    if raw.startswith("tuic://"):
        return _parse_tuic(raw)
    return None


def parse_all(raw_configs: list[str]) -> list[VPNConfig]:
    results = []
    for raw in raw_configs:
        cfg = parse_config(raw)
        if cfg and cfg.host not in ("?", "", None) and cfg.port > 0:
            results.append(cfg)
    return results
