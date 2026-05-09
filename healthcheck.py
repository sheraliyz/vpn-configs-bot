"""
Quick sanity check — runs WITHOUT sending to Telegram.
Usage: python healthcheck.py
"""
import sys, io
# Force UTF-8 output on Windows (avoid cp1251 emoji errors)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

from collections import Counter
from bot.fetcher import fetch_all_configs
from bot.parser import parse_all
from bot.validator import filter_reachable
from bot.notifier import _build_message

print("\n" + "=" * 60)
print("  VPN Configs Bot — Health Check")
print("=" * 60)

raw     = fetch_all_configs()
configs = parse_all(raw)

print(f"\n✅  Total raw configs fetched : {len(raw)}")
print(f"✅  Valid parsed configs      : {len(configs)}")

# Protocol distribution
counts = Counter(c.protocol for c in configs)
print("\n📊  Protocol breakdown:")
for proto, n in sorted(counts.items(), key=lambda x: -x[1]):
    print(f"    {proto:<14} {n}")

# Country distribution (top 10)
countries = Counter(c.country for c in configs)
print("\n🌍  Top countries:")
for country, n in countries.most_common(10):
    print(f"    {country:<28} {n}")

# TCP reachability check on a small sample
print("\n🔌  TCP reachability check (sample of 30 configs)...")
import random
sample = random.sample(configs, min(30, len(configs)))
alive  = filter_reachable(sample)
print(f"    {len(alive)}/{len(sample)} reachable ({len(alive)/len(sample)*100:.0f}% alive)")

# Caption length check
print("\n📝  Caption length check (first 10 configs):")
all_ok = True
for cfg in configs[:10]:
    msg = _build_message(cfg)
    ok  = len(msg) <= 4096
    if not ok:
        all_ok = False
    status = "OK  " if ok else "LONG"
    print(f"    [{status}] [{cfg.protocol}] {cfg.country} | {cfg.host}:{cfg.port} | {len(msg)}ch")

print(f"\n{'✅  All checks passed!' if all_ok else '❌  Issues found!'}")
print("=" * 60 + "\n")
