import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Telegram API credentials (from my.telegram.org)
# Using public fallback keys so user only has to configure BOT_TOKEN, OWNER_ID, and MONGO_DB_URI
API_ID = int(os.getenv("API_ID", "24961505"))
API_HASH = os.getenv("API_HASH", "a609d57a2b918a38c2a937a0ffc562e8")

# Bot Token (from @BotFather)
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Main Bot Owner Telegram ID (integer)
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

# MongoDB Connection URI
MONGO_DB_URI = os.getenv("MONGO_DB_URI", "")

# Default approval speed (requests per second)
DEFAULT_APPROVAL_SPEED = int(os.getenv("DEFAULT_APPROVAL_SPEED", "160"))

def is_configured() -> bool:
    """Check if required configuration options are set."""
    return bool(BOT_TOKEN) and OWNER_ID != 0 and bool(MONGO_DB_URI)
