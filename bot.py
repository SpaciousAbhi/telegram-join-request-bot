import asyncio
import logging
import time
import re
from pyrogram import Client, filters, raw, ContinuePropagation
from pyrogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, 
    InlineKeyboardButton, ChatMemberUpdated
)
from pyrogram.errors import (
    PeerIdInvalid, UserBlocked, UserIdInvalid,
    ChatAdminRequired, FloodWait, RPCError
)

import config
import database
import localization
import utils
import bulk_queue

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# State tracking for owner/user conversations
# Format: {user_id: {"state": "state_name", "data": {...}}}
USER_STATES = {}

# Active broadcasts list to track if a broadcast is running
# Format: {"is_running": False, "task": None}
BROADCAST_STATUS = {"is_running": False, "task": None}

# Initialize Client
app = Client(
    name="telegram_join_request_bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN
)

# ----------------- Helper Functions -----------------

async def show_language_selection(client: Client, chat_id: int):
    """Sends the language selection menu."""
    text = localization.get_text("choose_lang", "en")
    buttons = [
        [
            InlineKeyboardButton(localization.get_text("btn_lang_en", "en"), callback_data="setlang_en"),
            InlineKeyboardButton(localization.get_text("btn_lang_hi", "en"), callback_data="setlang_hi")
        ],
        [
            InlineKeyboardButton(localization.get_text("btn_lang_hinglish", "en"), callback_data="setlang_hinglish"),
            InlineKeyboardButton(localization.get_text("btn_lang_ur", "en"), callback_data="setlang_ur")
        ]
    ]
    await client.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def show_main_menu(client: Client, chat_id: int, lang: str):
    """Sends the main start menu for normal users."""
    text = localization.get_text("start_instruction", lang)
    bot_info = await client.get_me()
    bot_username = bot_info.username
    
    # Generate admin add links
    add_channel_url = f"https://t.me/{bot_username}?startchannel=true&admin=invite_users"
    add_group_url = f"https://t.me/{bot_username}?startgroup=true&admin=invite_users"
    
    buttons = [
        [
            InlineKeyboardButton(localization.get_text("btn_add_channel", lang), url=add_channel_url),
            InlineKeyboardButton(localization.get_text("btn_add_group", lang), url=add_group_url)
        ],
        [
            InlineKeyboardButton(localization.get_text("btn_bulk_approve", lang), callback_data="bulk_select"),
            InlineKeyboardButton(localization.get_text("btn_my_chats", lang), callback_data="my_chats")
        ],
        [
            InlineKeyboardButton(localization.get_text("btn_support", lang), url="https://t.me/Venom_Stone_Network"),
            InlineKeyboardButton(localization.get_text("btn_change_lang", lang), callback_data="change_lang")
        ]
    ]
    
    # Add an Admin Panel button if owner
    if utils.is_owner(chat_id):
        buttons.append([InlineKeyboardButton("👑 𝗢𝗪𝗡𝗘𝗥 𝗣𝗔𝗡𝗘𝗟", callback_data="owner_panel")])
        
    await client.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def handle_fsub_check(client: Client, chat_id: int, user_id: int) -> bool:
    """
    Checks force subscription. If missing, sends the FSub menu and returns False.
    If complete, returns True.
    """
    fsub_enabled = await database.get_setting("fsub_enabled", "0")
    if fsub_enabled != "1":
        return True
        
    missing = await utils.get_missing_fsub_chats(client, user_id)
    if not missing:
        return True
        
    # Send FSub menu listing only missing chats
    text = localization.get_text("fsub_title", "en") + "\n\n" + localization.get_text("fsub_msg", "en") + "\n"
    buttons = []
    
    for idx, chat in enumerate(missing, start=1):
        chat_title = chat["chat_title"]
        invite_link = chat["invite_link"]
        text += f"\n{idx}. 📢 <b>{chat_title}</b>"
        
        # Determine button label based on whether it is a request to join or normal join
        btn_label = "📢 𝗝𝗢𝗜𝗡 𝗖𝗛𝗔𝗡𝗡𝗘𝗟"
        if chat.get("is_request_to_join", 0) == 1:
            btn_label = "⚡ 𝗥𝗘𝗤𝗨𝗘𝗦𝗧 𝗧𝗢 𝗝𝗢𝗜𝗡"
            
        buttons.append([InlineKeyboardButton(btn_label, url=invite_link)])
        
    buttons.append([InlineKeyboardButton(localization.get_text("fsub_joined_btn", "en"), callback_data="fsub_check")])
    
    await client.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return False

# ----------------- Broadcast Process -----------------

async def broadcast_worker(client: Client, owner_id: int, message_to_copy: Message):
    """Asynchronous background worker to send a message to all users."""
    BROADCAST_STATUS["is_running"] = True
    users = await database.get_all_users()
    total = len(users)
    
    if total == 0:
        await client.send_message(owner_id, "❌ 𝗡𝗼 𝘂𝘀𝗲𝗿𝘀 found in the database to broadcast to.")
        BROADCAST_STATUS["is_running"] = False
        return
        
    progress_msg = await client.send_message(owner_id, "📢 <b>Starting broadcast...</b>")
    
    sent = 0
    failed = 0
    blocked = 0
    start_time = time.time()
    last_update = 0
    
    for idx, user in enumerate(users, start=1):
        user_id = user["user_id"]
        
        # Don't send to owner again unless desired, but we can send anyway
        try:
            await message_to_copy.copy(chat_id=user_id)
            sent += 1
        except UserBlocked:
            blocked += 1
            await database.set_user_banned(user_id, True) # Mark as banned/blocked
        except PeerIdInvalid:
            failed += 1
        except FloodWait as fw:
            await asyncio.sleep(fw.value + 1)
            # Retry
            try:
                await message_to_copy.copy(chat_id=user_id)
                sent += 1
            except Exception:
                failed += 1
        except Exception as e:
            logger.error(f"Failed to copy broadcast to {user_id}: {e}")
            failed += 1
            
        # Throttled status updates
        now = time.time()
        if now - last_update > 5 or idx == total:
            last_update = now
            elapsed = now - start_time
            speed = int((idx / elapsed) * 60) if elapsed > 0 else 0
            pct = int((idx / total) * 100)
            
            progress_text = (
                f"📢 <b>𝗕𝗥𝗢𝗔𝗗𝗖𝗔𝗦𝗧 𝗜𝗡 𝗣𝗥𝗢𝗚𝗥𝗘𝗦𝗦...</b>\n\n"
                f"📈 𝗣𝗿𝗼𝗴𝗿𝗲𝘀𝘀: {pct}%\n"
                f"👥 𝗧𝗼𝘁𝗮𝗹 𝗨𝘀𝗲𝗿𝘀: {total}\n"
                f"🟢 𝗦𝗲𝗻𝘁: {sent}\n"
                f"🚫 𝗕𝗹𝗼𝗰𝗸𝗲𝗱: {blocked}\n"
                f"❌ 𝗙𝗮𝗶𝗹𝗲𝗱: {failed}\n"
                f"🚀 𝗦𝗽𝗲𝗲𝗱: {speed} msg/min\n"
                f"⏳ 𝗥𝗲𝗺𝗮𝗶𝗻𝗶𝗻𝗴: {total - idx}"
            )
            try:
                await progress_msg.edit_text(progress_text)
            except Exception:
                pass
                
        # Small sleep to prevent flood
        await asyncio.sleep(0.05)
        
    duration = int(time.time() - start_time)
    final_report = (
        f"🎉 <b>𝗕𝗥𝗢𝗔𝗗𝗖𝗔𝗦𝗧 𝗖𝗢𝗠𝗣𝗟𝗘𝗧𝗘𝗗!</b>\n\n"
        f"⏱️ 𝗗𝘂𝗿𝗮𝘁𝗶𝗼𝗻: {duration} seconds\n"
        f"👥 𝗧𝗼𝘁𝗮𝗹 𝗨𝘀𝗲𝗿𝘀: {total}\n"
        f"🟢 𝗦𝗲𝗻𝘁: {sent}\n"
        f"🚫 𝗕𝗹𝗼𝗰𝗸𝗲𝗱: {blocked}\n"
        f"❌ 𝗙𝗮𝗶𝗹𝗲𝗱: {failed}"
    )
    await client.send_message(owner_id, final_report)
    BROADCAST_STATUS["is_running"] = False

# ----------------- Message Logging Handler (Pre-propagation) -----------------

@app.on_message(filters.private, group=-1)
async def log_private_message(client: Client, message: Message):
    user_id = message.from_user.id if message.from_user else 0
    text_content = message.text or "[Non-text message]"
    logger.info(f"📩 RECEIVED PRIVATE MESSAGE: user_id={user_id}, text='{text_content}'")
    raise ContinuePropagation

# ----------------- Start Handler -----------------

@app.on_message(filters.command("start") & filters.private)
async def handle_start(client: Client, message: Message):
    user_id = message.from_user.id
    username = message.from_user.username
    logger.info(f"🚀 Handling /start command for user_id={user_id}, username={username}")
    
    try:
        # 1. Register User in Database
        await database.add_user(user_id, username)
        logger.info(f"✅ User {user_id} registered/updated in database.")
        
        user_db = await database.get_user(user_id)
        logger.info(f"👤 User database profile: {user_db}")
        
        if user_db["is_banned"] == 1:
            logger.warning(f"🚫 Banned user {user_id} tried to use /start.")
            await message.reply_text("❌ 𝗬𝗼𝘂 𝗮𝗿𝗲 𝗯𝗮𝗻𝗻𝗲𝗱 from using this bot.")
            return
        
        # Check if there's a payload
        payload = ""
        if len(message.command) > 1:
            payload = message.command[1]
            logger.info(f"📦 Start payload found: {payload}")
            
        # 2. Check for Verification Payload (e.g. verify_CHATID)
        if payload.startswith("verify_"):
            try:
                # Parse chat ID from payload
                parts = payload.split("_")
                chat_id = int(parts[1])
                logger.info(f"🔒 Handling verification for user_id={user_id} in chat_id={chat_id}")
                
                # Verify user in database
                await database.set_user_verified(user_id, True)
                
                # Retrieve chat details
                chat_details = await database.get_chat(chat_id)
                chat_title = chat_details["chat_title"] if chat_details else f"Chat {chat_id}"
                
                # Approve pending request
                try:
                    await client.approve_chat_join_request(chat_id, user_id)
                    await database.increment_chat_approvals(chat_id)
                    await database.set_setting(f"pending_req_{chat_id}_{user_id}", "0")
                    
                    success_msg = localization.get_text("verify_success", user_db["lang"] or "en", chat_title=chat_title)
                    await message.reply_text(success_msg)
                    logger.info(f"✅ Auto-approved request for verified user {user_id} in chat {chat_id}")
                except Exception as e:
                    logger.error(f"❌ Failed to approve request after verification: {e}")
                    await message.reply_text("❌ Verification successful but failed to approve request automatically. Please notify the admin.")
            except Exception as e:
                logger.error(f"❌ Error handling verification payload: {e}")
                await message.reply_text("❌ Invalid verification link.")
            return
            
        # 3. Normal /start Flow (Check Force Sub)
        logger.info(f"⏳ Checking Force Subscription for user_id={user_id}")
        passed_fsub = await handle_fsub_check(client, user_id, user_id)
        if not passed_fsub:
            logger.info(f"⚠️ User {user_id} failed force subscription check.")
            return
            
        # 4. Language Selection Flow
        if not user_db["lang"]:
            logger.info(f"🌐 Prompting language selection for user_id={user_id}")
            await show_language_selection(client, user_id)
        else:
            logger.info(f"🏠 Showing main menu to user_id={user_id} with lang={user_db['lang']}")
            await show_main_menu(client, user_id, user_db["lang"])
    except Exception as e:
        logger.exception(f"💥 Exception in handle_start for user_id={user_id}: {e}")

# ----------------- Chat Join Request Handler -----------------

@app.on_chat_join_request()
async def handle_join_request(client: Client, join_request):
    chat = join_request.chat
    user = join_request.from_user
    chat_id = chat.id
    user_id = user.id
    
    logger.info(f"Join request received in {chat.title} ({chat_id}) from {user.first_name} ({user_id})")
    
    # Verify the chat is registered in database and active
    chat_db = await database.get_chat(chat_id)
    if not chat_db or chat_db["is_active"] == 0:
        # Chat is not connected or deactivated, skip auto-approval
        return
        
    if chat_db["auto_approve"] == 0:
        # Auto-approve is disabled for this chat
        return

    # Check if verification system is active globally
    verification_enabled = await database.get_setting("verification_enabled", "0")
    
    if verification_enabled == "1":
        # Hidden verification flow: send DM to user
        await database.set_setting(f"pending_req_{chat_id}_{user_id}", "1")
        
        bot_info = await client.get_me()
        bot_username = bot_info.username
        verify_url = f"https://t.me/{bot_username}?start=verify_{chat_id}"
        
        # Get user's preferred language or default to English
        user_db = await database.get_user(user_id)
        lang = user_db["lang"] if (user_db and user_db["lang"]) else "en"
        
        text = localization.get_text("verify_msg", lang, chat_title=chat.title)
        buttons = [[InlineKeyboardButton(localization.get_text("verify_btn", lang), url=verify_url)]]
        
        try:
            await client.send_message(
                chat_id=user_id,
                text=text,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            logger.info(f"Sent verification DM to {user_id} for chat {chat_id}")
        except Exception as e:
            # "If verification is ON but the bot cannot message the joining user, the bot should log that request as failed or pending and show the reason only in owner/admin logs."
            logger.error(f"Cannot message user {user_id} for join request verification: {e}. Keeping request pending.")
            # Store error details in DB log or just output to terminal log
            await database.set_setting(f"err_{chat_id}_{user_id}", f"Verification ON, but DM failed: {e}")
    else:
        # Instant Auto Approval
        try:
            await client.approve_chat_join_request(chat_id, user_id)
            await database.increment_chat_approvals(chat_id)
            logger.info(f"Automatically approved join request for user {user_id} in {chat_id}")
        except Exception as e:
            logger.error(f"Failed instant auto-approval for {user_id} in {chat_id}: {e}")

# ----------------- Bot Connection (my_chat_member) Handler -----------------

@app.on_chat_member_updated()
async def handle_my_chat_member(client: Client, update: ChatMemberUpdated):
    bot_id = client.me.id
    
    # We only care about updates regarding the bot itself
    target_user = None
    if update.new_chat_member:
        target_user = update.new_chat_member.user
    elif update.old_chat_member:
        target_user = update.old_chat_member.user
        
    if not target_user or target_user.id != bot_id:
        return

    chat = update.chat
    new_member = update.new_chat_member
    old_member = update.old_chat_member
    chat_id = chat.id
    
    # Get user who added the bot (from_user is the executor of the status change)
    installer_id = update.from_user.id if update.from_user else 0
    installer_username = update.from_user.username if (update.from_user and update.from_user.username) else ""
    
    # 1. Added as admin
    if new_member.status in ("administrator", "owner"):
        logger.info(f"Bot added as admin in chat {chat.title} ({chat_id}) by user {installer_id}")
        
        chat_type = str(chat.type).split('.')[-1].lower() # "channel", "group", "supergroup"
        username = chat.username or ""
        
        # Save chat to database
        # If installer_id is 0, we try to see if we already have a record or use default admin config
        owner_id = installer_id if installer_id != 0 else config.OWNER_ID
        
        await database.add_chat(
            chat_id=chat_id,
            title=chat.title,
            chat_type=chat_type,
            username=username,
            owner_id=owner_id
        )
        
        # Fetch detailed reports
        details = await utils.get_chat_details(client, chat_id)
        if not details:
            return
            
        admin_status = localization.get_text("admin_active", "en")
        permissions_status = "🟢 𝗙𝗨𝗟𝗟 𝗣𝗘𝗥𝗠𝗜𝗦𝗦𝗜𝗢𝗡𝗦" if details["has_required_perms"] else localization.get_text("permission_missing_warning", "en")
        auto_approve_status = localization.get_text("active", "en")
        
        # Prepare the connection report DM to installer
        if installer_id != 0:
            user_db = await database.get_user(installer_id)
            lang = user_db["lang"] if (user_db and user_db["lang"]) else "en"
            
            report_title = localization.get_text("chat_report_title", lang)
            report_body = localization.get_text(
                "chat_report_details", 
                lang,
                chat_title=chat.title,
                chat_id=chat_id,
                username=username or "None",
                chat_type=chat_type.upper(),
                member_count=details["member_count"],
                admin_status=admin_status,
                permissions_status=permissions_status,
                auto_approve_status=auto_approve_status
            )
            
            # Setup immediate bulk approval button
            buttons = [
                [InlineKeyboardButton("⚡ 𝗔𝗣𝗣𝗥𝗢𝗩𝗘 𝗔𝗟𝗟 𝗢𝗟𝗗 𝗣𝗘𝗡𝗗𝗜𝗡𝗚 𝗥𝗘𝗤𝗨𝗘𝗦𝗧𝗦", callback_data=f"bulk_start_{chat_id}")],
                [InlineKeyboardButton(localization.get_text("btn_my_chats", lang), callback_data="my_chats")]
            ]
            
            try:
                await client.send_message(
                    chat_id=installer_id,
                    text=f"{report_title}\n\n{report_body}",
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
            except Exception as e:
                logger.error(f"Could not send connection DM to user {installer_id}: {e}")
                
    # 2. Removed from chat or admin status revoked
    elif old_member.status in ("administrator", "member", "restricted") and new_member.status in ("left", "kicked"):
        logger.info(f"Bot removed from chat {chat.title} ({chat_id})")
        await database.update_chat_status(chat_id, False)
        
        # Notify the owner of the chat
        chat_data = await database.get_chat(chat_id)
        if chat_data:
            owner_id = chat_data["owner_id"]
            try:
                await client.send_message(
                    chat_id=owner_id,
                    text=f"🔴 <b>𝗕𝗼𝘁 𝗥𝗲𝗺𝗼𝘃𝗲𝗱/𝗞𝗶𝗰𝗸𝗲𝗱:</b> The bot was removed from chat <b>{chat.title}</b>. This chat is now marked as inactive."
                )
            except Exception:
                pass
                
    elif new_member.status in ("member", "restricted"):
        # Member but not admin: permissions missing warning
        logger.info(f"Bot added to chat {chat.title} ({chat_id}) but not admin")
        if installer_id != 0:
            try:
                await client.send_message(
                    chat_id=installer_id,
                    text=f"⚠️ <b>𝗕𝗼𝘁 𝗶𝘀 𝗻𝗼𝘁 𝗔𝗱𝗺𝗶𝗻:</b> You added the bot to <b>{chat.title}</b> but did not give admin permissions. The bot requires admin permissions with <b>Invite Users via Link</b> enabled to auto-approve requests."
                )
            except Exception:
                pass

@app.on_message(filters.command("admin") & filters.private)
async def handle_admin_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    logger.info(f"👑 Handling /admin command for user_id={user_id}")
    
    try:
        if not utils.is_owner(user_id):
            logger.warning(f"⚠️ Non-owner user {user_id} attempted to access /admin.")
            return
            
        logger.info(f"🔓 Access granted to owner {user_id} for admin panel.")
        await show_owner_panel(client, user_id)
    except Exception as e:
        logger.exception(f"💥 Exception in handle_admin_cmd: {e}")

async def show_owner_panel(client: Client, user_id: int):
    """Sends the admin/owner control panel."""
    stats = await database.get_db_stats()
    
    fsub_enabled = await database.get_setting("fsub_enabled", "0")
    fsub_icon = "🟢 𝗢𝗡" if fsub_enabled == "1" else "🔴 𝗢𝗙𝗙"
    
    verification_enabled = await database.get_setting("verification_enabled", "0")
    verification_icon = "🟢 𝗢𝗡" if verification_enabled == "1" else "🔴 𝗢𝗙𝗙"
    
    bulk_enabled = await database.get_setting("bulk_enabled", "1")
    bulk_icon = "🟢 𝗢𝗡" if bulk_enabled == "1" else "🔴 𝗢𝗙𝗙"
    
    speed = await database.get_setting("approval_speed", "160")
    
    # Lang stats string
    lang_str = ", ".join(f"<b>{k.upper()}</b>: {v}" for k, v in stats["lang_stats"].items())
    
    text = (
        f"👑 <b>𝗢𝗪𝗡𝗘𝗥 𝗖𝗢𝗡𝗧𝗥𝗢𝗟 𝗣𝗔𝗡𝗘𝗟</b>\n\n"
        f"👥 𝗧𝗼𝘁𝗮𝗹 𝗨𝘀𝗲𝗿𝘀: {stats['total_users']}\n"
        f"✅ 𝗩𝗲𝗿𝗶𝗳𝗶𝗲𝗱 𝗨𝘀𝗲𝗿𝘀: {stats['verified_users']}\n"
        f"⏳ 𝗣𝗲𝗻𝗱𝗶𝗻𝗴 𝗩𝗲𝗿𝗶𝗳𝗶𝗰𝗮𝘁𝗶𝗼𝗻: {stats['pending_verifications']}\n"
        f"🌐 𝗟𝗮𝗻𝗴𝘂𝗮𝗴𝗲 𝗦𝘁𝗮𝘁𝘀: {lang_str}\n\n"
        f"📊 𝗖𝗼𝗻𝗻𝗲𝗰𝘁𝗲𝗱 𝗖𝗵𝗮𝘁𝘀: {stats['total_chats']}\n"
        f"🟢 𝗧𝗼𝘁𝗮𝗹 𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱: {stats['total_approved']}\n"
        f"📢 𝗙𝗼𝗿𝗰𝗲 𝗦𝘂𝗯 𝗖𝗵𝗮𝘁𝘀: {stats['fsub_count']}\n"
        f"⚡ 𝗔𝗰𝘁𝗶𝘃𝗲 𝗕𝘂𝗹𝗸 𝗝𝗼𝗯𝘀: {stats['active_bulk_jobs']}\n\n"
        f"⚙️ 𝗙𝗼𝗿𝗰𝗲 𝗦𝘂𝗯: {fsub_icon}\n"
        f"🤖 𝗛𝗶𝗱𝗱𝗲𝗻 𝗩𝗲𝗿𝗶𝗳𝗶𝗰𝗮𝘁𝗶𝗼𝗻: {verification_icon}\n"
        f"⚡ 𝗕𝘂𝗹𝗸 𝗔𝗽𝗽𝗿𝗼𝘃𝗮𝗹: {bulk_icon}\n"
        f"🚀 𝗔𝗽𝗽𝗿𝗼𝘃𝗮𝗹 𝗦𝗽𝗲𝗲𝗱: {speed} req/min\n\n"
        f"𝗩𝗘𝗡𝗢𝗠 𝗦𝗧𝗢𝗡𝗘 𝗡𝗘𝗧𝗪𝗢𝗥𝗞"
    )
    
    buttons = [
        [
            InlineKeyboardButton(f"📢 𝗙𝗼𝗿𝗰𝗲 𝗦𝘂𝗯: {fsub_icon}", callback_data="toggle_fsub"),
            InlineKeyboardButton(f"🤖 𝗩𝗲𝗿𝗶𝗳𝗶𝗰𝗮𝘁𝗶𝗼𝗻: {verification_icon}", callback_data="toggle_verify")
        ],
        [
            InlineKeyboardButton(f"⚡ 𝗕𝘂𝗹𝗸: {bulk_icon}", callback_data="toggle_bulk"),
            InlineKeyboardButton(f"🚀 𝗦𝗽𝗲𝗲𝗱: {speed}/m", callback_data="set_speed_menu")
        ],
        [
            InlineKeyboardButton("📢 𝗕𝗥𝗢𝗔𝗗𝗖𝗔𝗦𝗧", callback_data="owner_broadcast"),
            InlineKeyboardButton("📢 𝗠𝗔𝗡𝗔𝗚𝗘 𝗙𝗦𝗨𝗕 𝗖𝗛𝗔𝗧𝗦", callback_data="owner_manage_fsub")
        ],
        [
            InlineKeyboardButton("📊 𝗖𝗢𝗡𝗡𝗘𝗖𝗧𝗘𝗗 𝗖𝗛𝗔𝗧𝗦", callback_data="owner_chats"),
            InlineKeyboardButton("❌ 𝗠𝗔𝗡𝗔𝗚𝗘 𝗨𝗦𝗘𝗥𝗦", callback_data="owner_manage_users")
        ],
        [InlineKeyboardButton("❌ 𝗖𝗟𝗢𝗦𝗘", callback_data="close_panel")]
    ]
    
    await client.send_message(
        chat_id=user_id,
        text=text,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ----------------- Message Handlers for Inputs (State Catchers) -----------------

@app.on_message(filters.private & ~filters.command(["start", "admin"]))
async def handle_private_inputs(client: Client, message: Message):
    user_id = message.from_user.id
    user_state = USER_STATES.get(user_id)
    
    if not user_state:
        # Check if they are just replying normally
        return
        
    state = user_state["state"]
    
    # 1. Catching Broadcast Message
    if state == "AWAITING_BROADCAST_MSG":
        # Save message reference
        USER_STATES[user_id] = {
            "state": "CONFIRMING_BROADCAST",
            "message": message
        }
        
        # Show preview and confirmation
        await message.reply_text("📢 <b>𝗕𝗥𝗢𝗔𝗗𝗖𝗔𝗦𝗧 𝗣𝗥𝗘𝗩𝗜𝗘𝗪:</b>\nBelow is how your message will look:")
        await message.copy(chat_id=user_id)
        
        buttons = [
            [
                InlineKeyboardButton("✅ 𝗦𝗘𝗡𝗗 / 𝗖𝗢𝗡𝗙𝗜𝗥𝗠", callback_data="confirm_broadcast"),
                InlineKeyboardButton("❌ 𝗖𝗔𝗡𝗖𝗘𝗟", callback_data="cancel_broadcast")
            ]
        ]
        await message.reply_text(
            text="⚠️ 𝗖𝗼𝗻𝗳𝗶𝗿𝗺 𝗯𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁? This will copy this message to all registered users.",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return
        
    # 2. Catching Force Sub Chat ID / Username / Forward / Invite Link
    elif state == "AWAITING_FSUB_CHAT":
        chat_id_val = None
        chat_title = ""
        invite_link = ""
        
        # Case A: Forwarded message
        if message.forward_from_chat:
            chat_id_val = message.forward_from_chat.id
            chat_title = message.forward_from_chat.title
            invite_link = message.forward_from_chat.username
            if invite_link:
                invite_link = f"https://t.me/{invite_link}"
        else:
            # Case B: Entered invite link, username or numeric ID
            txt = message.text.strip()
            
            # Numeric ID
            if txt.startswith("-100") or txt.isdigit() or (txt.startswith("-") and txt[1:].isdigit()):
                try:
                    chat_id_val = int(txt)
                except ValueError:
                    pass
            # Username
            elif txt.startswith("@"):
                chat_id_val = txt
            # Link
            elif "t.me/" in txt:
                # Resolve username if public link
                m = re.search(r"t\.me/([a-zA-Z0-9_]+)", txt)
                if m:
                    username = m.group(1)
                    if username.lower() not in ("joinchat", "+"):
                        chat_id_val = f"@{username}"
                        invite_link = txt
                    else:
                        invite_link = txt
                else:
                    invite_link = txt
            else:
                await message.reply_text("❌ Invalid input. Please forward a message from the chat, enter a numeric ID (like -100...), username (starts with @), or invite link.")
                return
                
        # Resolve details
        if chat_id_val:
            try:
                chat_info = await client.get_chat(chat_id_val)
                chat_id_val = chat_info.id
                chat_title = chat_info.title
                if not invite_link:
                    invite_link = chat_info.invite_link or (f"https://t.me/{chat_info.username}" if chat_info.username else "")
            except Exception as e:
                # If we cannot resolve, we may need to ask owner to input manually or we fail if it's private and we aren't in it.
                logger.error(f"Cannot resolve chat {chat_id_val}: {e}")
                
        if not chat_id_val:
            # If we could not resolve, ask for chat ID manually or let them set it manually
            await message.reply_text("❌ Chat could not be resolved automatically. Please ensure the bot is admin in that chat and try entering the numeric Chat ID directly.")
            return
            
        USER_STATES[user_id] = {
            "state": "AWAITING_FSUB_LINK",
            "chat_id": chat_id_val,
            "chat_title": chat_title or f"Chat {chat_id_val}",
            "invite_link": invite_link
        }
        
        # Ask for invite link if not resolved
        if not invite_link:
            await message.reply_text(f"📢 Resolved: <b>{chat_title}</b> (<code>{chat_id_val}</code>).\n\n🔗 Please enter the invite link for this chat:")
        else:
            # Skip to request to join prompt
            await prompt_fsub_request_to_join(client, user_id)
            
    elif state == "AWAITING_FSUB_LINK":
        link = message.text.strip()
        if not (link.startswith("http://") or link.startswith("https://") or "t.me/" in link):
            await message.reply_text("❌ Invalid link. Please enter a valid URL:")
            return
            
        USER_STATES[user_id]["invite_link"] = link
        await prompt_fsub_request_to_join(client, user_id)
        
    # 3. Catching Ban/Unban User ID
    elif state == "AWAITING_BAN_ID":
        txt = message.text.strip()
        if not txt.isdigit():
            await message.reply_text("❌ Please enter a valid numeric User ID:")
            return
            
        target_id = int(txt)
        await database.set_user_banned(target_id, True)
        USER_STATES.pop(user_id, None)
        await message.reply_text(f"✅ User <code>{target_id}</code> has been banned from using the bot.")
        await show_owner_panel(client, user_id)
        
    elif state == "AWAITING_UNBAN_ID":
        txt = message.text.strip()
        if not txt.isdigit():
            await message.reply_text("❌ Please enter a valid numeric User ID:")
            return
            
        target_id = int(txt)
        await database.set_user_banned(target_id, False)
        USER_STATES.pop(user_id, None)
        await message.reply_text(f"✅ User <code>{target_id}</code> has been unbanned.")
        await show_owner_panel(client, user_id)

async def prompt_fsub_request_to_join(client: Client, user_id: int):
    """Asks if the force-sub chat is a request-to-join chat."""
    data = USER_STATES[user_id]
    buttons = [
        [
            InlineKeyboardButton("✅ 𝗬𝗘𝗦 (𝗥𝗲𝗾𝘂𝗲𝘀𝘁)", callback_data="fsub_req_yes"),
            InlineKeyboardButton("❌ 𝗡𝗢 (𝗡𝗼𝗿𝗺𝗮𝗹 𝗝𝗼𝗶𝗻)", callback_data="fsub_req_no")
        ]
    ]
    await client.send_message(
        chat_id=user_id,
        text=f"📢 <b>{data['chat_title']}</b>\nInvite Link: {data['invite_link']}\n\n❓ Is this a 'Request to Join' chat? (Does it require admin approval?)",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ----------------- Callback Query Handler -----------------

@app.on_callback_query()
async def handle_callbacks(client: Client, callback_query: CallbackQuery):
    data = callback_query.data
    user_id = callback_query.from_user.id
    user_db = await database.get_user(user_id)
    lang = user_db["lang"] if (user_db and user_db["lang"]) else "en"
    
    # --- LANGUAGE SELECTION ---
    if data.startswith("setlang_"):
        selected_lang = data.split("_")[1]
        await database.set_user_lang(user_id, selected_lang)
        # Ack callback
        await callback_query.answer("Language Selected!")
        # Delete selection screen
        await callback_query.message.delete()
        # Show main menu
        await show_main_menu(client, user_id, selected_lang)
        return
        
    elif data == "change_lang":
        await callback_query.message.delete()
        await show_language_selection(client, user_id)
        return

    # --- FORCE SUBSCRIPTION SYSTEM ---
    elif data == "fsub_check":
        # Check Force Sub again
        missing = await utils.get_missing_fsub_chats(client, user_id)
        if not missing:
            await callback_query.answer("✅ Thank you! Access unlocked.", show_alert=True)
            await callback_query.message.delete()
            # Proceed to language selection or main menu
            user_db = await database.get_user(user_id)
            if not user_db["lang"]:
                await show_language_selection(client, user_id)
            else:
                await show_main_menu(client, user_id, user_db["lang"])
        else:
            # Answer with warning alert
            await callback_query.answer(localization.get_text("fsub_please_join", lang), show_alert=True)
            
            # Edit the message to show only remaining chats
            text = localization.get_text("fsub_title", lang) + "\n\n" + localization.get_text("fsub_msg", lang) + "\n"
            buttons = []
            for idx, chat in enumerate(missing, start=1):
                chat_title = chat["chat_title"]
                invite_link = chat["invite_link"]
                text += f"\n{idx}. 📢 <b>{chat_title}</b>"
                
                btn_label = "📢 𝗝𝗢𝗜𝗡 𝗖𝗛𝗔𝗡𝗡𝗘𝗟"
                if chat.get("is_request_to_join", 0) == 1:
                    btn_label = "⚡ 𝗥𝗘𝗤𝗨𝗘𝗦𝗧 𝗧𝗢 𝗝𝗢𝗜𝗡"
                    
                buttons.append([InlineKeyboardButton(btn_label, url=invite_link)])
                
            buttons.append([InlineKeyboardButton(localization.get_text("fsub_joined_btn", lang), callback_data="fsub_check")])
            
            try:
                await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
            except Exception:
                pass
        return

    # --- CHAT SETTINGS PANEL (Normal User) ---
    elif data == "my_chats":
        chats = await database.get_owner_chats(user_id)
        if not chats:
            await callback_query.answer(localization.get_text("no_chats", lang), show_alert=True)
            return
            
        await callback_query.message.delete()
        
        text = localization.get_text("chat_list_title", lang)
        buttons = []
        for chat in chats:
            chat_title = chat["chat_title"]
            chat_id = chat["chat_id"]
            buttons.append([InlineKeyboardButton(f"📊 {chat_title}", callback_data=f"chat_settings_{chat_id}")])
            
        buttons.append([InlineKeyboardButton(localization.get_text("btn_home", lang), callback_data="home")])
        await client.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return
        
    elif data.startswith("chat_settings_"):
        chat_id = int(data.split("_")[2])
        chat_db = await database.get_chat(chat_id)
        
        if not chat_db or chat_db["owner_id"] != user_id:
            await callback_query.answer("❌ Access Denied.")
            return
            
        # Get live permissions
        details = await utils.get_chat_details(client, chat_id)
        if details:
            # Update info in DB
            await database.add_chat(chat_id, details["title"], details["type"], details["username"], user_id)
            perms_ok = details["has_required_perms"]
            member_count = details["member_count"]
            admin_status = localization.get_text("admin_active", lang)
        else:
            perms_ok = False
            member_count = 0
            admin_status = localization.get_text("admin_inactive", lang)
            
        # Permission status warning text
        permissions_status = "🟢 𝗙𝗨𝗟𝗟 𝗣𝗘𝗥𝗠𝗜𝗦𝗦𝗜𝗢𝗡𝗦" if perms_ok else localization.get_text("permission_missing_warning", lang)
        
        auto_approve_status = localization.get_text("active", lang) if chat_db["auto_approve"] == 1 else localization.get_text("inactive", lang)
        
        text = (
            f"⚙️ <b>{localization.get_text('chat_settings_title', lang, chat_title=chat_db['chat_title'])}</b>\n\n"
            f"🆔 𝗜𝗗: <code>{chat_id}</code>\n"
            f"👥 𝗠𝗲𝗺𝗯𝗲𝗿𝘀: {member_count}\n"
            f"🛡️ 𝗔𝗱𝗺𝗶𝗻: {admin_status}\n"
            f"⚙️ 𝗣𝗲𝗿𝗺𝗶𝘀𝘀𝗶𝗼𝗻𝘀: {permissions_status}\n"
            f"🤖 𝗔𝘂𝘁𝗼-𝗔𝗽𝗽𝗿𝗼𝘃𝗲: {auto_approve_status}\n"
            f"🟢 𝗧𝗼𝘁𝗮𝗹 𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱: {chat_db['total_approved']}"
        )
        
        # Approve toggle buttons
        btn_approve_toggle = (
            InlineKeyboardButton(localization.get_text("btn_auto_approve_on", lang), callback_data=f"toggle_approve_{chat_id}")
            if chat_db["auto_approve"] == 1
            else InlineKeyboardButton(localization.get_text("btn_auto_approve_off", lang), callback_data=f"toggle_approve_{chat_id}")
        )
        
        buttons = [
            [btn_approve_toggle],
            [
                InlineKeyboardButton(localization.get_text("btn_bulk_approve_this", lang), callback_data=f"bulk_start_{chat_id}"),
                InlineKeyboardButton(localization.get_text("btn_remove_chat", lang), callback_data=f"chat_remove_{chat_id}")
            ],
            [InlineKeyboardButton(localization.get_text("btn_back", lang), callback_data="my_chats")]
        ]
        
        await callback_query.message.delete()
        await client.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return
        
    elif data.startswith("toggle_approve_"):
        chat_id = int(data.split("_")[2])
        chat_db = await database.get_chat(chat_id)
        if not chat_db or chat_db["owner_id"] != user_id:
            await callback_query.answer("❌ Access Denied.")
            return
            
        new_val = 0 if chat_db["auto_approve"] == 1 else 1
        await database.set_chat_auto_approve(chat_id, bool(new_val))
        
        await callback_query.answer("Auto-Approve status toggled!")
        # Reload settings page
        # Simply call the callback simulation
        callback_query.data = f"chat_settings_{chat_id}"
        await handle_callbacks(client, callback_query)
        return
        
    elif data.startswith("chat_remove_"):
        chat_id = int(data.split("_")[2])
        chat_db = await database.get_chat(chat_id)
        if not chat_db or chat_db["owner_id"] != user_id:
            await callback_query.answer("❌ Access Denied.")
            return
            
        text = localization.get_text("confirm_remove", lang, chat_title=chat_db["chat_title"])
        buttons = [
            [
                InlineKeyboardButton(localization.get_text("btn_confirm_yes", lang), callback_data=f"confirm_remove_yes_{chat_id}"),
                InlineKeyboardButton(localization.get_text("btn_confirm_no", lang), callback_data=f"chat_settings_{chat_id}")
            ]
        ]
        await callback_query.message.delete()
        await client.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return
        
    elif data.startswith("confirm_remove_yes_"):
        chat_id = int(data.split("_")[3])
        chat_db = await database.get_chat(chat_id)
        if not chat_db or chat_db["owner_id"] != user_id:
            await callback_query.answer("❌ Access Denied.")
            return
            
        await database.remove_chat(chat_id)
        await callback_query.answer("Chat removed and deactivated!")
        callback_query.data = "my_chats"
        await handle_callbacks(client, callback_query)
        return

    # --- BULK APPROVAL SYSTEM PANEL ---
    elif data == "bulk_select":
        # Global bulk approval check
        bulk_enabled = await database.get_setting("bulk_enabled", "1")
        if bulk_enabled != "1":
            await callback_query.answer("❌ Bulk approval is currently disabled globally by the owner.", show_alert=True)
            return
            
        chats = await database.get_owner_chats(user_id)
        if not chats:
            await callback_query.answer(localization.get_text("bulk_no_chats", lang), show_alert=True)
            return
            
        if len(chats) == 1:
            # Automatically start bulk for single chat
            chat_id = chats[0]["chat_id"]
            callback_query.data = f"bulk_start_{chat_id}"
            await handle_callbacks(client, callback_query)
            return
            
        # If multiple chats, show select menu
        await callback_query.message.delete()
        text = localization.get_text("bulk_select_chat", lang)
        buttons = []
        for chat in chats:
            chat_title = chat["chat_title"]
            chat_id = chat["chat_id"]
            buttons.append([InlineKeyboardButton(f"⚡ {chat_title}", callback_data=f"bulk_start_{chat_id}")])
            
        buttons.append([InlineKeyboardButton(localization.get_text("btn_home", lang), callback_data="home")])
        await client.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return
        
    elif data.startswith("bulk_start_"):
        chat_id = int(data.split("_")[2])
        chat_db = await database.get_chat(chat_id)
        if not chat_db or chat_db["owner_id"] != user_id:
            await callback_query.answer("❌ Access Denied.")
            return
            
        # Verify permissions
        details = await utils.get_chat_details(client, chat_id)
        if not details or not details["has_required_perms"]:
            await callback_query.answer("⚠️ Cannot run bulk approval. Bot lacks admin permissions to invite users/approve join requests.", show_alert=True)
            return
            
        # Show start confirmation and trigger worker
        await callback_query.answer("Starting Bulk Approval...")
        
        # Start background job
        # We need progress message ID. We can edit this message
        await bulk_queue.start_bulk_job(
            client=client,
            chat_id=chat_id,
            owner_id=user_id,
            progress_msg_id=callback_query.message.id,
            lang=lang
        )
        return
        
    elif data.startswith("bulk_pause_"):
        chat_id = int(data.split("_")[2])
        await bulk_queue.pause_bulk_job(chat_id)
        await callback_query.answer("Paused bulk approval.")
        return
        
    elif data.startswith("bulk_resume_"):
        chat_id = int(data.split("_")[2])
        await bulk_queue.resume_bulk_job(chat_id)
        await callback_query.answer("Resumed bulk approval.")
        return
        
    elif data.startswith("bulk_stop_"):
        chat_id = int(data.split("_")[2])
        await bulk_queue.stop_bulk_job(chat_id)
        await callback_query.answer("Stopped bulk approval.")
        return
        
    elif data.startswith("bulk_refresh_"):
        chat_id = int(data.split("_")[2])
        job = bulk_queue.ACTIVE_BULK_JOBS.get(chat_id)
        if job:
            await job.update_status_msg(force=True)
            await callback_query.answer("Refreshed status.")
        else:
            await callback_query.answer("Job is no longer active.")
        return

    # --- HOME / CLOSE PANELS ---
    elif data == "home":
        await callback_query.message.delete()
        await show_main_menu(client, user_id, lang)
        return
        
    elif data == "close_panel":
        await callback_query.message.delete()
        return

    # --- OWNER PANEL ACTIONS (Owner Only) ---
    if not utils.is_owner(user_id):
        return
        
    if data == "owner_panel":
        await callback_query.message.delete()
        await show_owner_panel(client, user_id)
        return
        
    elif data == "toggle_fsub":
        val = await database.get_setting("fsub_enabled", "0")
        new_val = "1" if val == "0" else "0"
        await database.set_setting("fsub_enabled", new_val)
        await callback_query.answer(f"Force Subscription: {'Enabled' if new_val == '1' else 'Disabled'}")
        
        callback_query.data = "owner_panel"
        await handle_callbacks(client, callback_query)
        return
        
    elif data == "toggle_verify":
        val = await database.get_setting("verification_enabled", "0")
        new_val = "1" if val == "0" else "0"
        await database.set_setting("verification_enabled", new_val)
        await callback_query.answer(f"Hidden Verification: {'Enabled' if new_val == '1' else 'Disabled'}")
        
        callback_query.data = "owner_panel"
        await handle_callbacks(client, callback_query)
        return
        
    elif data == "toggle_bulk":
        val = await database.get_setting("bulk_enabled", "1")
        new_val = "1" if val == "0" else "0"
        await database.set_setting("bulk_enabled", new_val)
        await callback_query.answer(f"Bulk Approvals: {'Enabled' if new_val == '1' else 'Disabled'}")
        
        callback_query.data = "owner_panel"
        await handle_callbacks(client, callback_query)
        return
        
    elif data == "set_speed_menu":
        await callback_query.message.delete()
        text = "🚀 𝗦𝗘𝗟𝗘𝗖𝗧 𝗕𝗨𝗟𝗞 𝗔𝗣𝗣𝗥𝗢𝗩𝗔𝗟 𝗦𝗣𝗘𝗘𝗗"
        speeds = [10, 50, 100, 200, 500, 1000]
        buttons = []
        for s in speeds:
            buttons.append([InlineKeyboardButton(f"🚀 {s} req/min", callback_data=f"set_speed_{s}")])
            
        buttons.append([InlineKeyboardButton("⬅️ 𝗕𝗔𝗖𝗞", callback_data="owner_panel")])
        await client.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return
        
    elif data.startswith("set_speed_"):
        speed_val = data.split("_")[2]
        await database.set_setting("approval_speed", speed_val)
        await callback_query.answer(f"Speed set to {speed_val} req/min")
        
        callback_query.data = "owner_panel"
        await handle_callbacks(client, callback_query)
        return
        
    elif data == "owner_broadcast":
        if BROADCAST_STATUS["is_running"]:
            await callback_query.answer("⚠️ A broadcast is already running. Please wait for it to finish.", show_alert=True)
            return
            
        await callback_query.message.delete()
        USER_STATES[user_id] = {"state": "AWAITING_BROADCAST_MSG"}
        
        buttons = [[InlineKeyboardButton("❌ 𝗖𝗔𝗡𝗖𝗘𝗟", callback_data="owner_panel")]]
        await client.send_message(
            chat_id=user_id,
            text="📢 <b>𝗦𝗘𝗡𝗗 𝗬𝗢𝗨𝗥 𝗕𝗥𝗢𝗔𝗗𝗖𝗔𝗦𝗧 𝗠𝗘𝗦𝗦𝗔𝗚𝗘</b>\n\nSend me the message you want to broadcast. It can contain formatted text, inline buttons, links, emojis, media, photos, videos, or documents. You can also forward the message here directly.",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return
        
    elif data == "confirm_broadcast":
        state_data = USER_STATES.get(user_id)
        if not state_data or state_data["state"] != "CONFIRMING_BROADCAST":
            await callback_query.answer("❌ Timeout or invalid state.")
            return
            
        await callback_query.message.delete()
        msg_to_copy = state_data["message"]
        USER_STATES.pop(user_id, None)
        
        # Start background worker task
        BROADCAST_STATUS["task"] = asyncio.create_task(broadcast_worker(client, user_id, msg_to_copy))
        return
        
    elif data == "cancel_broadcast":
        USER_STATES.pop(user_id, None)
        await callback_query.answer("Broadcast cancelled.")
        callback_query.data = "owner_panel"
        await handle_callbacks(client, callback_query)
        return
        
    elif data == "owner_manage_fsub":
        fsubs = await database.get_fsub_chats()
        await callback_query.message.delete()
        
        text = "📢 <b>𝗠𝗔𝗡𝗔𝗚𝗘 𝗙𝗢𝗥𝗖𝗘 𝗦𝗨𝗕𝗦𝗖𝗥𝗜𝗣𝗧𝗜𝗢𝗡 𝗖𝗛𝗔𝗧𝗦</b>\n\nClick a chat below to remove it, or add a new one."
        buttons = []
        for chat in fsubs:
            title = chat["chat_title"]
            chat_id = chat["chat_id"]
            buttons.append([InlineKeyboardButton(f"❌ {title}", callback_data=f"remove_fsub_{chat_id}")])
            
        buttons.append([InlineKeyboardButton("➕ 𝗔𝗗𝗗 𝗙𝗦𝗨𝗕 𝗖𝗛𝗔𝗧", callback_data="add_fsub")])
        buttons.append([InlineKeyboardButton("⬅️ 𝗕𝗔𝗖𝗞", callback_data="owner_panel")])
        
        await client.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return
        
    elif data == "add_fsub":
        await callback_query.message.delete()
        USER_STATES[user_id] = {"state": "AWAITING_FSUB_CHAT"}
        
        buttons = [[InlineKeyboardButton("❌ 𝗖𝗔𝗡𝗖𝗘𝗟", callback_data="owner_manage_fsub")]]
        await client.send_message(
            chat_id=user_id,
            text=(
                "➕ <b>𝗔𝗗𝗗 𝗙𝗢𝗥𝗖𝗘 𝗦𝗨𝗕𝗦𝗖𝗥𝗜𝗣𝗧𝗜𝗢𝗡 𝗖𝗛𝗔𝗧</b>\n\n"
                "Please perform one of the following:\n"
                "1. Forward a message from that channel/group here.\n"
                "2. Enter the numeric Chat ID (e.g. <code>-10023456789</code>).\n"
                "3. Enter the public username (e.g. <code>@MyChannel</code>).\n"
                "4. Enter the invite link (e.g. <code>t.me/+AbCdEfGh</code>)."
            ),
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return
        
    elif data.startswith("remove_fsub_"):
        chat_id = int(data.split("_")[2])
        await database.remove_fsub_chat(chat_id)
        await callback_query.answer("Force sub chat removed!")
        callback_query.data = "owner_manage_fsub"
        await handle_callbacks(client, callback_query)
        return
        
    elif data.startswith("fsub_req_"):
        val = data.split("_")[2]
        is_req = True if val == "yes" else False
        
        state_data = USER_STATES.get(user_id)
        if not state_data or state_data["state"] != "AWAITING_FSUB_LINK":
            await callback_query.answer("❌ Invalid state.")
            return
            
        chat_id = state_data["chat_id"]
        chat_title = state_data["chat_title"]
        invite_link = state_data["invite_link"]
        
        await database.add_fsub_chat(chat_id, chat_title, invite_link, is_req)
        USER_STATES.pop(user_id, None)
        
        await callback_query.answer("Force Sub Chat Added Successfully!")
        await callback_query.message.delete()
        callback_query.data = "owner_manage_fsub"
        await handle_callbacks(client, callback_query)
        return
        
    elif data == "owner_chats":
        chats = await database.get_all_chats()
        await callback_query.message.delete()
        
        text = "📊 <b>𝗔𝗟𝗟 𝗖𝗢𝗡𝗡𝗘𝗖𝗧𝗘𝗗 𝗖𝗛𝗔𝗧𝗦 (𝗚𝗟𝗢𝗕𝗔𝗟)</b>"
        buttons = []
        for chat in chats:
            title = chat["chat_title"]
            chat_id = chat["chat_id"]
            owner = chat["owner_id"]
            buttons.append([InlineKeyboardButton(f"📊 {title} (Owner: {owner})", callback_data=f"owner_chat_details_{chat_id}")])
            
        buttons.append([InlineKeyboardButton("⬅️ 𝗕𝗔𝗖𝗞", callback_data="owner_panel")])
        await client.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return
        
    elif data.startswith("owner_chat_details_"):
        chat_id = int(data.split("_")[3])
        chat_db = await database.get_chat(chat_id)
        if not chat_db:
            await callback_query.answer("❌ Chat not found.")
            return
            
        details = await utils.get_chat_details(client, chat_id)
        member_count = details["member_count"] if details else 0
        
        text = (
            f"👑 <b>𝗖𝗛𝗔𝗧 𝗗𝗘𝗧𝗔𝗜𝗟𝗦 (𝗔𝗗𝗠𝗜𝗡 𝗩𝗜𝗘𝗪)</b>\n\n"
            f"📝 𝗧𝗶𝘁𝗹𝗲: {chat_db['chat_title']}\n"
            f"🆔 𝗜𝗗: <code>{chat_id}</code>\n"
            f"👤 𝗢𝘄𝗻𝗲𝗿 𝗜𝗗: <code>{chat_db['owner_id']}</code>\n"
            f"👥 𝗠𝗲𝗺𝗯𝗲𝗿𝘀: {member_count}\n"
            f"🤖 𝗔𝘂𝘁𝗼-𝗔𝗽𝗽𝗿𝗼𝘃𝗲: {'🟢 ON' if chat_db['auto_approve'] == 1 else '🔴 OFF'}\n"
            f"🟢 𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱: {chat_db['total_approved']}"
        )
        
        buttons = [
            [InlineKeyboardButton("❌ 𝗙𝗢𝗥𝗖𝗘 𝗥𝗘𝗠𝗢𝗩𝗘", callback_data=f"owner_force_remove_{chat_id}")],
            [InlineKeyboardButton("⬅️ 𝗕𝗔𝗖𝗞", callback_data="owner_chats")]
        ]
        await callback_query.message.delete()
        await client.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return
        
    elif data.startswith("owner_force_remove_"):
        chat_id = int(data.split("_")[3])
        await database.remove_chat(chat_id)
        await callback_query.answer("Chat force-removed and deactivated!")
        callback_query.data = "owner_chats"
        await handle_callbacks(client, callback_query)
        return
        
    elif data == "owner_manage_users":
        await callback_query.message.delete()
        text = "❌ <b>𝗠𝗔𝗡𝗔𝗚𝗘 𝗨𝗦𝗘𝗥𝗦</b>\n\nChoose an action:"
        buttons = [
            [
                InlineKeyboardButton("🚫 𝗕𝗔𝗡 𝗨𝗦𝗘𝗥", callback_data="owner_ban_user"),
                InlineKeyboardButton("🟢 𝗨𝗡𝗕𝗔𝗡 𝗨𝗦𝗘𝗥", callback_data="owner_unban_user")
            ],
            [InlineKeyboardButton("⬅️ 𝗕𝗔𝗖𝗞", callback_data="owner_panel")]
        ]
        await client.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return
        
    elif data == "owner_ban_user":
        await callback_query.message.delete()
        USER_STATES[user_id] = {"state": "AWAITING_BAN_ID"}
        buttons = [[InlineKeyboardButton("❌ 𝗖𝗔𝗡𝗖𝗘𝗟", callback_data="owner_manage_users")]]
        await client.send_message(
            chat_id=user_id,
            text="🚫 Please enter the numeric User ID to ban:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return
        
    elif data == "owner_unban_user":
        await callback_query.message.delete()
        USER_STATES[user_id] = {"state": "AWAITING_UNBAN_ID"}
        buttons = [[InlineKeyboardButton("❌ 𝗖𝗔𝗡𝗖𝗘𝗟", callback_data="owner_manage_users")]]
        await client.send_message(
            chat_id=user_id,
            text="🟢 Please enter the numeric User ID to unban:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

# ----------------- Startup / Main Loop -----------------

async def main():
    # 1. Initialize Database
    await database.init_db()
    
    # 2. Start Pyrogram Client
    logger.info("Starting Telegram Join Request Bot...")
    await app.start()
    
    # Keep it running
    bot_info = await app.get_me()
    logger.info(f"Bot successfully started: @{bot_info.username}")
    
    # Print warning if credentials are not configured properly
    if not config.is_configured():
        logger.warning("Bot is NOT fully configured! Please verify API_ID, API_HASH, BOT_TOKEN, and OWNER_ID in .env.")
        
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
