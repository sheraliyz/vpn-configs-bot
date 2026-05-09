import logging
import os
import sys

os.makedirs("logs", exist_ok=True)

import config
from bot.storage import init_db
from bot.runner import run_check
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def main():
    logger.info("VPN Configs Bot starting...")
    init_db()

    # Immediate first run on startup
    try:
        count = run_check()
        if count == 0:
            logger.info("No new configs on startup.")
    except Exception as e:
        logger.error(f"Error on first run: {e}")

    scheduler = BlockingScheduler()
    scheduler.add_job(
        func=run_check,
        trigger=IntervalTrigger(hours=config.CHECK_INTERVAL_HOURS),
        id="vpn_configs_check",
        name="VPN configs check",
        misfire_grace_time=300,
    )

    logger.info(
        f"Scheduler started. Posting {config.CONFIGS_PER_RUN} config(s) "
        f"every {config.CHECK_INTERVAL_HOURS} hours."
    )

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")


if __name__ == "__main__":
    main()
