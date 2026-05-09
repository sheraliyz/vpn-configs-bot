import logging
import random
from config import CONFIGS_PER_RUN
from bot.fetcher import fetch_all_configs
from bot.parser import parse_all, VPNConfig
from bot.validator import filter_reachable
from bot.notifier import send_config
from bot.storage import is_posted, mark_posted, cleanup_old_records

logger = logging.getLogger(__name__)

# Preferred posting order (rarest/newest protocols first for variety)
PROTOCOL_PRIORITY = ["Hysteria2", "TUIC", "VLESS", "Trojan", "VMess", "Shadowsocks"]

# How many candidates to TCP-test before selecting CONFIGS_PER_RUN to post.
# Larger pool = more diversity but slower check. 150 is a good balance.
VALIDATE_POOL = 150


def _select_diverse(configs: list[VPNConfig], n: int) -> list[VPNConfig]:
    """
    Pick N configs with protocol diversity:
    - First pass: one config per protocol (shuffled within each group)
    - Second pass: fill remaining slots randomly
    """
    by_protocol: dict[str, list[VPNConfig]] = {}
    for cfg in configs:
        by_protocol.setdefault(cfg.protocol, []).append(cfg)

    # Shuffle within each protocol group
    for lst in by_protocol.values():
        random.shuffle(lst)

    selected: list[VPNConfig] = []

    # One of each protocol in priority order
    for proto in PROTOCOL_PRIORITY:
        if proto in by_protocol and by_protocol[proto]:
            selected.append(by_protocol[proto].pop(0))
        if len(selected) >= n:
            break

    # Fill remaining slots from the rest
    remaining = [c for lst in by_protocol.values() for c in lst]
    random.shuffle(remaining)
    for cfg in remaining:
        if len(selected) >= n:
            break
        selected.append(cfg)

    return selected[:n]


def run_check() -> int:
    logger.info("Starting VPN configs check...")

    raw_configs = fetch_all_configs()
    all_configs = parse_all(raw_configs)
    logger.info(f"Parsed valid configs: {len(all_configs)}")

    new_configs = [c for c in all_configs if not is_posted(c.id)]
    logger.info(f"New (unposted) configs: {len(new_configs)}")

    if not new_configs:
        logger.info("No new configs to post.")
        return 0

    # Pick a diverse candidate pool, then TCP-test them in parallel.
    # This ensures we only post configs whose servers are actually online.
    candidates = _select_diverse(new_configs, VALIDATE_POOL)
    logger.info(f"TCP-testing {len(candidates)} candidate configs...")
    reachable  = filter_reachable(candidates)

    if not reachable:
        logger.warning("No reachable configs found in candidate pool. Skipping.")
        return 0

    to_post = _select_diverse(reachable, CONFIGS_PER_RUN)

    sent = 0
    for cfg in to_post:
        if send_config(cfg):
            mark_posted(cfg.id, cfg.name, cfg.protocol)
            sent += 1

    cleanup_old_records(days=7)   # configs rotate — allow re-post after 7 days
    logger.info(f"Check complete. {sent} config(s) posted.")
    return sent
