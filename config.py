import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Telegram API credentials (from my.telegram.org)
API_ID = int(os.getenv("API_ID", "32043332"))
API_HASH = os.getenv("API_HASH", "b62729fb0bc4fe2eb1f6cb97d330cc6f")

# Bot Token (from @BotFather)
BOT_TOKEN = os.getenv("BOT_TOKEN", "8786730507:AAFczQzXCwDvTzxYPK-c202ryuI7yAI8No4")

# Main Bot Owner Telegram ID (integer)
OWNER_ID = int(os.getenv("OWNER_ID", "6938449843"))

# MongoDB Connection URI
MONGO_DB_URI = os.getenv("MONGO_DB_URI", "mongodb+srv://bicilag866_db_user:sqPoJgxSK3pdp9pY@cluster0.f80tzlt.mongodb.net/?appName=Cluster0")

# Default approval speed (requests per minute)
DEFAULT_APPROVAL_SPEED = int(os.getenv("DEFAULT_APPROVAL_SPEED", "160"))

# Persistent Pyrogram session string — generated once locally so Telegram always
# delivers updates to the same auth key, even across Heroku dyno restarts.
# Regenerate with: python generate_session.py
SESSION_STRING = os.getenv(
    "SESSION_STRING",
    "BQHo8UQAqwlnK2SFOot-e_8F62lTnl4ow7WVMIm8oplAcoHo-TZWdgM0ouNebRwccKUGCfo5bS45z-k6ctILHAk8jHvZnmlVji0ePW8f0BovpiaqtkWGapf1Rb0-BWtIoLVFwU9lBNJRr3G-uykdJOFgoOvpf-VBEqoYzKAYnkUmAoktLcvghsPr81zX_xVRfWQcp5SOupchYjLnXfP0gd_pQsZIRJVvkWJjVA38JugJc3vA_qkZcgIEWYu3ijG7lI4HAyQPqG868W3AbbLg48UmLbw9Ep83Tf2cMcEOj6nv-HJhqi7IIEfncWzxKFr_Kn1c48p5eItkE8JcGs6jGChqNVmdJAAAAAILut4LAQ"
)

def is_configured() -> bool:
    """Check if required configuration options are set."""
    return bool(BOT_TOKEN) and OWNER_ID != 0 and bool(MONGO_DB_URI)
