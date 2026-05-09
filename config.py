import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN            = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID              = os.getenv("TELEGRAM_CHAT_ID", "")
CHECK_INTERVAL_HOURS = int(os.getenv("CHECK_INTERVAL_HOURS", "4"))
CONFIGS_PER_RUN      = int(os.getenv("CONFIGS_PER_RUN", "3"))

if not BOT_TOKEN or not CHAT_ID:
    raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in .env!")
