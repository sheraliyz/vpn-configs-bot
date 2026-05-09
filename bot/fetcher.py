import base64
import logging
import requests

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

# Free config subscription sources — verified working (GitHub raw, no auth)
SOURCES = [
    # mahdibland V2RayAggregator — huge merged collection, updated daily
    "https://raw.githubusercontent.com/mahdibland/V2RayAggregator/master/sub/sub_merge.txt",
    # peasoft NoMoreWalls — plain-text, mixed protocols
    "https://raw.githubusercontent.com/peasoft/NoMoreWalls/master/list.txt",
    # ermaozi — plain-text subscription
    "https://raw.githubusercontent.com/ermaozi/get_subscribe/main/subscribe/v2ray.txt",
    # mfuu/v2ray — base64 encoded
    "https://raw.githubusercontent.com/mfuu/v2ray/master/v2ray",
    # Pawdroid Free-servers — base64
    "https://raw.githubusercontent.com/Pawdroid/Free-servers/master/sub",
    # w1770946466/Auto_proxy — long-term subscriptions (6 files)
    "https://raw.githubusercontent.com/w1770946466/Auto_proxy/main/Long_term_subscription1",
    "https://raw.githubusercontent.com/w1770946466/Auto_proxy/main/Long_term_subscription2",
    "https://raw.githubusercontent.com/w1770946466/Auto_proxy/main/Long_term_subscription3",
    "https://raw.githubusercontent.com/w1770946466/Auto_proxy/main/Long_term_subscription4",
    "https://raw.githubusercontent.com/w1770946466/Auto_proxy/main/Long_term_subscription5",
    "https://raw.githubusercontent.com/w1770946466/Auto_proxy/main/Long_term_subscription6",
    # Leon406/SubCrawler — per-protocol feeds
    "https://raw.githubusercontent.com/Leon406/SubCrawler/master/sub/share/vless",
    "https://raw.githubusercontent.com/Leon406/SubCrawler/master/sub/share/hysteria2",
    "https://raw.githubusercontent.com/Leon406/SubCrawler/master/sub/share/ss",
]

SUPPORTED_PREFIXES = (
    "vless://",
    "vmess://",
    "trojan://",
    "hysteria2://",
    "hy2://",
    "ss://",
    "tuic://",
)


def _decode_content(raw: str) -> str:
    """Try base64 decode if content is not already plain configs."""
    stripped = raw.strip()
    # Already plain text
    if any(stripped.startswith(p) for p in SUPPORTED_PREFIXES):
        return stripped
    # Try base64 decode
    try:
        padded = stripped + "=" * (4 - len(stripped) % 4)
        decoded = base64.b64decode(padded).decode("utf-8", errors="ignore")
        if any(decoded.startswith(p) for p in SUPPORTED_PREFIXES):
            return decoded
    except Exception:
        pass
    return stripped


def fetch_from_url(url: str) -> list[str]:
    """Fetch and decode configs from one subscription URL."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        content = _decode_content(resp.text)
        configs = [
            line.strip()
            for line in content.splitlines()
            if line.strip() and any(line.strip().startswith(p) for p in SUPPORTED_PREFIXES)
        ]
        source = url.split("/")[-1] or url.split("/")[-2]
        logger.debug(f"[Fetcher] {source}: {len(configs)} configs")
        return configs
    except Exception as e:
        logger.warning(f"[Fetcher] Failed {url}: {e}")
        return []


def fetch_all_configs() -> list[str]:
    """Fetch from all sources, return deduplicated raw config strings."""
    all_configs: list[str] = []
    seen: set[str] = set()

    for url in SOURCES:
        for cfg in fetch_from_url(url):
            if cfg not in seen:
                seen.add(cfg)
                all_configs.append(cfg)

    logger.info(f"[Fetcher] Total unique raw configs: {len(all_configs)}")
    return all_configs
