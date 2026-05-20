import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists.
load_dotenv()


def _get_int(name: str, default: int = 0) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value.strip())
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer, got {value!r}") from exc


# Telegram API credentials from my.telegram.org.
# Keep the public fallback for one-click deploys, but override it in production
# if Telegram ever rate-limits or revokes these shared credentials.
API_ID = _get_int("API_ID", 32043332)
API_HASH = os.getenv("API_HASH", "b62729fb0bc4fe2eb1f6cb97d330cc6f").strip()

# Bot token from @BotFather. This must come from the runtime environment.
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Main bot owner Telegram ID.
OWNER_ID = _get_int("OWNER_ID", 0)

# MongoDB connection URI.
MONGO_DB_URI = os.getenv("MONGO_DB_URI", "").strip()

# Default approval speed in requests per minute.
DEFAULT_APPROVAL_SPEED = _get_int("DEFAULT_APPROVAL_SPEED", 160)


def is_configured() -> bool:
    """Check if required configuration options are set."""
    return bool(BOT_TOKEN) and OWNER_ID != 0 and bool(MONGO_DB_URI)


def missing_required_config() -> list[str]:
    missing = []
    if not BOT_TOKEN:
        missing.append("BOT_TOKEN")
    if OWNER_ID == 0:
        missing.append("OWNER_ID")
    if not MONGO_DB_URI:
        missing.append("MONGO_DB_URI")
    return missing
