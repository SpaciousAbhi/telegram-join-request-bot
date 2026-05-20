import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Telegram API credentials (from my.telegram.org)
API_ID = int(os.getenv("API_ID", "24961505"))
API_HASH = os.getenv("API_HASH", "a609d57a2b918a38c2a937a0ffc562e8")

# Bot Token (from @BotFather)
BOT_TOKEN = os.getenv("BOT_TOKEN", "8786730507:AAFczQzXCwDvTzxYPK-c202ryuI7yAI8No4")

# Main Bot Owner Telegram ID (integer)
OWNER_ID = int(os.getenv("OWNER_ID", "6938449843"))

# MongoDB Connection URI
MONGO_DB_URI = os.getenv("MONGO_DB_URI", "mongodb+srv://bicilag866_db_user:sqPoJgxSK3pdp9pY@cluster0.f80tzlt.mongodb.net/?appName=Cluster0")

# Default approval speed (requests per second)
DEFAULT_APPROVAL_SPEED = int(os.getenv("DEFAULT_APPROVAL_SPEED", "160"))

def is_configured() -> bool:
    """Check if required configuration options are set."""
    return bool(BOT_TOKEN) and OWNER_ID != 0 and bool(MONGO_DB_URI)
