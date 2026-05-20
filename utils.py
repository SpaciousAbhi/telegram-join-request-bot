import logging
from pyrogram import Client, raw
from pyrogram.errors import UserNotParticipant, ChatAdminRequired, RPCError
import database

logger = logging.getLogger(__name__)

def is_owner(user_id: int) -> bool:
    """Checks if the user is the bot owner."""
    import config
    return user_id == config.OWNER_ID

async def check_admin_permissions(client: Client, chat_id: int) -> dict:
    """
    Checks if the bot is an admin in the chat and retrieves its permissions.
    Specifically checks for 'can_invite_users' (which is needed to approve join requests).
    Returns a dict with 'is_admin' and 'has_required_perms'.
    """
    try:
        member = await client.get_chat_member(chat_id, "me")
        if member.status in ("administrator", "owner"):
            # Check for required permissions
            # In channels, we need 'can_invite_users'
            # In groups, we need 'can_invite_users'
            privileges = member.privileges
            has_required = False
            if privileges:
                has_required = privileges.can_invite_users or False
                
            return {
                "is_admin": True,
                "has_required_perms": has_required,
                "privileges": privileges
            }
        else:
            return {
                "is_admin": False,
                "has_required_perms": False,
                "privileges": None
            }
    except Exception as e:
        logger.error(f"Error checking admin permissions for chat {chat_id}: {e}")
        return {
            "is_admin": False,
            "has_required_perms": False,
            "privileges": None
        }

async def get_chat_details(client: Client, chat_id: int) -> dict:
    """
    Fetches chat metadata including title, type, username, member count, and admin status.
    """
    try:
        chat = await client.get_chat(chat_id)
        admin_info = await check_admin_permissions(client, chat_id)
        
        # Get member count if possible
        member_count = 0
        try:
            member_count = await client.get_chat_members_count(chat_id)
        except Exception:
            # For some private chats/channels it might fail if not admin
            if chat.members_count:
                member_count = chat.members_count
                
        return {
            "chat_id": chat.id,
            "title": chat.title,
            "type": str(chat.type).split('.')[-1].lower(), # "channel", "group", "supergroup"
            "username": chat.username or "",
            "member_count": member_count,
            "is_admin": admin_info["is_admin"],
            "has_required_perms": admin_info["has_required_perms"]
        }
    except Exception as e:
        logger.error(f"Error fetching chat details for {chat_id}: {e}")
        return None

async def check_user_joined_chat(client: Client, chat_id: int, user_id: int) -> bool:
    """
    Checks if a user has joined a chat or has a pending join request.
    Handles both normal membership and request-to-join checks.
    """
    # 1. Check if user is a member of the chat
    try:
        member = await client.get_chat_member(chat_id, user_id)
        if member.status in ("member", "administrator", "owner", "restricted"):
            return True
    except UserNotParticipant:
        # User is not a participant, check for pending join request
        pass
    except Exception as e:
        logger.debug(f"Error checking membership for user {user_id} in {chat_id}: {e}")
        
    # 2. Check if there is a recorded join request in our database
    db_pending = await database.get_setting(f"pending_req_{chat_id}_{user_id}", "0")
    if db_pending == "1":
        return True

    # 3. Fallback: query MTProto GetChatInviteImporters
    try:
        peer = await client.resolve_peer(chat_id)
        # Search by user ID if possible (we can try to query first page or use search query q)
        # We try to search by query string (e.g. user ID or username/name)
        user_info = None
        try:
            user_info = await client.get_users(user_id)
        except Exception:
            pass
            
        q_str = str(user_id)
        if user_info and user_info.username:
            q_str = user_info.username
            
        result = await client.invoke(
            raw.functions.messages.GetChatInviteImporters(
                peer=peer,
                requested=True,
                q=q_str,
                limit=10,
                offset_date=0,
                offset_user=raw.types.InputUserEmpty()
            )
        )
        
        # Check if user is in returned list
        for importer in result.importers:
            if importer.user_id == user_id:
                # Save to database cache so we don't call this slow method again
                await database.set_setting(f"pending_req_{chat_id}_{user_id}", "1")
                return True
                
        # Try a quick search with first name if query by ID/username didn't return
        if user_info and user_info.first_name:
            result = await client.invoke(
                raw.functions.messages.GetChatInviteImporters(
                    peer=peer,
                    requested=True,
                    q=user_info.first_name,
                    limit=20,
                    offset_date=0,
                    offset_user=raw.types.InputUserEmpty()
                )
            )
            for importer in result.importers:
                if importer.user_id == user_id:
                    await database.set_setting(f"pending_req_{chat_id}_{user_id}", "1")
                    return True
                    
    except Exception as e:
        logger.debug(f"MTProto check for user {user_id} in {chat_id} failed: {e}")
        
    return False

async def get_missing_fsub_chats(client: Client, user_id: int) -> list:
    """
    Returns a list of force-subscription chats that the user HAS NOT joined/requested yet.
    """
    fsub_chats = await database.get_fsub_chats()
    if not fsub_chats:
        return []
        
    missing = []
    for chat in fsub_chats:
        joined = await check_user_joined_chat(client, chat["chat_id"], user_id)
        if not joined:
            missing.append(chat)
            
    return missing
