import logging
import time
from motor.motor_asyncio import AsyncIOMotorClient
import config

logger = logging.getLogger(__name__)

# Global MongoDB Client and Database instances
client = None
db = None

async def init_db():
    """Initializes the MongoDB connection and seeds default settings."""
    global client, db
    
    if not config.MONGO_DB_URI:
        logger.error("MONGO_DB_URI is not set! Cannot initialize database connection.")
        return
        
    try:
        # Initialize Motor Async Client
        client = AsyncIOMotorClient(config.MONGO_DB_URI)
        # Retrieves DB specified in URI or falls back to 'telegram_bot'
        db = client.get_default_database("telegram_bot")
        logger.info("MongoDB client connected successfully.")
        
        # Seed default settings
        defaults = {
            "fsub_enabled": "0",          # 0 = OFF, 1 = ON
            "verification_enabled": "0",  # 0 = OFF, 1 = ON
            "bulk_enabled": "1",          # 0 = Disabled, 1 = Enabled
            "approval_speed": "160"       # Default requests per minute
        }
        
        for k, v in defaults.items():
            await db.settings.update_one(
                {"_id": k},
                {"$setOnInsert": {"value": v}},
                upsert=True
            )
        logger.info("Default settings seeded successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize MongoDB database: {e}")
        raise e

# User Operations
async def get_user(user_id: int):
    if db is None: return None
    user = await db.users.find_one({"_id": user_id})
    if user:
        user["user_id"] = user["_id"]
    return user

async def add_user(user_id: int, username: str = None):
    if db is None: return
    await db.users.update_one(
        {"_id": user_id},
        {
            "$set": {"username": username},
            "$setOnInsert": {
                "lang": None,
                "is_verified": 0,
                "is_banned": 0,
                "created_at": time.time()
            }
        },
        upsert=True
    )

async def set_user_lang(user_id: int, lang: str):
    if db is None: return
    await db.users.update_one({"_id": user_id}, {"$set": {"lang": lang}})

async def set_user_verified(user_id: int, is_verified: bool):
    if db is None: return
    val = 1 if is_verified else 0
    await db.users.update_one({"_id": user_id}, {"$set": {"is_verified": val}})

async def set_user_banned(user_id: int, is_banned: bool):
    if db is None: return
    val = 1 if is_banned else 0
    await db.users.update_one({"_id": user_id}, {"$set": {"is_banned": val}})

async def get_all_users():
    if db is None: return []
    users = []
    async for doc in db.users.find({}):
        doc["user_id"] = doc["_id"]
        users.append(doc)
    return users

# Chat Operations
async def get_chat(chat_id: int):
    if db is None: return None
    chat = await db.chats.find_one({"_id": chat_id})
    if chat:
        chat["chat_id"] = chat["_id"]
    return chat

async def add_chat(chat_id: int, title: str, chat_type: str, username: str, owner_id: int):
    if db is None: return
    await db.chats.update_one(
        {"_id": chat_id},
        {
            "$set": {
                "chat_title": title,
                "chat_type": chat_type,
                "username": username,
                "owner_id": owner_id,
                "is_active": 1
            },
            "$setOnInsert": {
                "auto_approve": 1,
                "total_approved": 0,
                "created_at": time.time()
            }
        },
        upsert=True
    )

async def update_chat_status(chat_id: int, is_active: bool):
    if db is None: return
    val = 1 if is_active else 0
    await db.chats.update_one({"_id": chat_id}, {"$set": {"is_active": val}})

async def set_chat_auto_approve(chat_id: int, auto_approve: bool):
    if db is None: return
    val = 1 if auto_approve else 0
    await db.chats.update_one({"_id": chat_id}, {"$set": {"auto_approve": val}})

async def increment_chat_approvals(chat_id: int):
    if db is None: return
    await db.chats.update_one({"_id": chat_id}, {"$inc": {"total_approved": 1}})

async def get_owner_chats(owner_id: int):
    if db is None: return []
    chats = []
    async for doc in db.chats.find({"owner_id": owner_id, "is_active": 1}):
        doc["chat_id"] = doc["_id"]
        chats.append(doc)
    return chats

async def get_all_chats():
    if db is None: return []
    chats = []
    async for doc in db.chats.find({"is_active": 1}):
        doc["chat_id"] = doc["_id"]
        chats.append(doc)
    return chats

async def remove_chat(chat_id: int):
    if db is None: return
    await db.chats.update_one({"_id": chat_id}, {"$set": {"is_active": 0}})

# Force Subscription Operations
async def add_fsub_chat(chat_id: int, chat_title: str, invite_link: str, is_request_to_join: bool = False):
    if db is None: return
    val = 1 if is_request_to_join else 0
    await db.force_subs.update_one(
        {"_id": chat_id},
        {
            "$set": {
                "chat_title": chat_title,
                "invite_link": invite_link,
                "is_request_to_join": val,
                "created_at": time.time()
            }
        },
        upsert=True
    )

async def remove_fsub_chat(chat_id: int):
    if db is None: return
    await db.force_subs.delete_one({"_id": chat_id})

async def get_fsub_chats():
    if db is None: return []
    fsubs = []
    async for doc in db.force_subs.find({}):
        doc["chat_id"] = doc["_id"]
        fsubs.append(doc)
    return fsubs

# Settings Operations
async def get_setting(key: str, default: str = None) -> str:
    if db is None: return default
    doc = await db.settings.find_one({"_id": key})
    return doc["value"] if doc else default

async def set_setting(key: str, value: str):
    if db is None: return
    await db.settings.update_one(
        {"_id": key},
        {"$set": {"value": str(value)}},
        upsert=True
    )

# Bulk Jobs Operations
async def get_bulk_job(chat_id: int):
    if db is None: return None
    job = await db.bulk_jobs.find_one({"_id": chat_id})
    if job:
        job["chat_id"] = job["_id"]
    return job

async def save_bulk_job(chat_id: int, total: int, approved: int, failed: int, skipped: int, status: str):
    if db is None: return
    await db.bulk_jobs.update_one(
        {"_id": chat_id},
        {
            "$set": {
                "total_count": total,
                "approved_count": approved,
                "failed_count": failed,
                "skipped_count": skipped,
                "status": status,
                "updated_at": time.time()
            }
        },
        upsert=True
    )

async def delete_bulk_job(chat_id: int):
    if db is None: return
    await db.bulk_jobs.delete_one({"_id": chat_id})

async def get_all_bulk_jobs():
    if db is None: return []
    jobs = []
    async for doc in db.bulk_jobs.find({}):
        doc["chat_id"] = doc["_id"]
        jobs.append(doc)
    return jobs

# Global Statistics for Owner Panel
async def get_db_stats():
    if db is None:
        return {
            "total_users": 0, "verified_users": 0, "pending_verifications": 0,
            "lang_stats": {}, "total_chats": 0, "total_approved": 0,
            "fsub_count": 0, "active_bulk_jobs": 0, "failed_bulk_jobs": 0
        }
        
    total_users = await db.users.count_documents({})
    verified_users = await db.users.count_documents({"is_verified": 1})
    pending_verifications = await db.users.count_documents({"is_verified": 0})
    
    # Retrieve language group counts
    lang_stats = {}
    cursor = db.users.aggregate([{"$group": {"_id": "$lang", "count": {"$sum": 1}}}])
    async for doc in cursor:
        lang_code = doc["_id"] or "not_selected"
        lang_stats[lang_code] = doc["count"]
        
    total_chats = await db.chats.count_documents({"is_active": 1})
    
    # Calculate sum of approved requests across chats
    total_approved = 0
    cursor = db.chats.aggregate([{"$group": {"_id": None, "total": {"$sum": "$total_approved"}}}])
    async for doc in cursor:
        total_approved = doc["total"]
        
    fsub_count = await db.force_subs.count_documents({})
    active_bulk_jobs = await db.bulk_jobs.count_documents({"status": "running"})
    failed_bulk_jobs = await db.bulk_jobs.count_documents({"status": "stopped"})
    
    return {
        "total_users": total_users,
        "verified_users": verified_users,
        "pending_verifications": pending_verifications,
        "lang_stats": lang_stats,
        "total_chats": total_chats,
        "total_approved": total_approved,
        "fsub_count": fsub_count,
        "active_bulk_jobs": active_bulk_jobs,
        "failed_bulk_jobs": failed_bulk_jobs
    }
