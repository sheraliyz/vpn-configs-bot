"""
TCP reachability check — verifies host:port is accepting connections
before posting a config. Does NOT test VPN functionality, only
that the server endpoint is online and accepting TCP connections.
"""
import logging
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from bot.parser import VPNConfig

logger = logging.getLogger(__name__)

TIMEOUT = 4       # seconds per connection attempt
MAX_WORKERS = 40  # parallel checks


def _tcp_ok(host: str, port: int) -> bool:
    """Return True if host:port accepts a TCP connection within TIMEOUT seconds."""
    try:
        with socket.create_connection((host, port), timeout=TIMEOUT):
            return True
    except Exception:
        return False


def filter_reachable(configs: list[VPNConfig]) -> list[VPNConfig]:
    """
    Return only configs whose host:port responds to a TCP connection.
    Uses a thread pool so all checks run in parallel.
    """
    if not configs:
        return []

    results: dict[str, bool] = {}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        future_to_cfg = {
            pool.submit(_tcp_ok, cfg.host, cfg.port): cfg
            for cfg in configs
        }
        for future in as_completed(future_to_cfg):
            cfg = future_to_cfg[future]
            try:
                results[cfg.id] = future.result()
            except Exception:
                results[cfg.id] = False

    reachable = [c for c in configs if results.get(c.id, False)]
    total     = len(configs)
    alive     = len(reachable)
    dead      = total - alive

    logger.info(
        f"[Validator] {alive}/{total} configs reachable "
        f"({dead} dead, {alive/total*100:.0f}% alive)"
    )
    return reachable
