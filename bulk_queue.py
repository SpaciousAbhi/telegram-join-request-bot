import asyncio
import time
import logging
from pyrogram import raw, Client
from pyrogram.errors import FloodWait, RPCError
import database
import localization

logger = logging.getLogger(__name__)

# Dictionary to keep track of active bulk approval jobs in memory
# Key: chat_id (int), Value: BulkJob instance
ACTIVE_BULK_JOBS = {}

class BulkJob:
    def __init__(self, client: Client, chat_id: int, owner_id: int, progress_msg_id: int, lang: str):
        self.client = client
        self.chat_id = chat_id
        self.owner_id = owner_id
        self.progress_msg_id = progress_msg_id
        self.lang = lang
        
        self.status = "running" # "running", "paused", "stopped", "completed"
        self.total_count = 0
        self.approved_count = 0
        self.failed_count = 0
        self.skipped_count = 0
        self.remaining_count = 0
        
        self.task = None
        self.pause_cond = asyncio.Condition()
        self.start_time = time.time()
        self.speed = 0 # req/min
        self.last_update_time = 0
        
        # Track skipped users so we don't try them again in this run
        self.skipped_user_ids = set()

    async def update_status_msg(self, force=False):
        """Edits the progress message in Telegram, throttled to avoid rate limits."""
        now = time.time()
        if not force and (now - self.last_update_time < 5):
            return
            
        self.last_update_time = now
        
        # Calculate speed (req/min)
        elapsed = now - self.start_time
        total_processed = self.approved_count + self.failed_count + self.skipped_count
        if elapsed > 1:
            self.speed = int((total_processed / elapsed) * 60)
        else:
            self.speed = 0
            
        progress_pct = 100
        if self.total_count > 0:
            progress_pct = min(100, int((total_processed / self.total_count) * 100))
            
        status_icons = {
            "running": "🚀",
            "paused": "⏸️",
            "stopped": "⛔",
            "completed": "🎉"
        }
        
        status_icon = status_icons.get(self.status, "⚙️")
        
        # Format values using bold translation
        text = localization.get_text(
            "bulk_status_msg",
            lang=self.lang,
            chat_title=f"Chat {self.chat_id}", # Fallback
            status_icon=status_icon,
            status=self.status.upper(),
            progress_pct=progress_pct,
            total=self.total_count,
            approved=self.approved_count,
            failed=self.failed_count,
            skipped=self.skipped_count,
            remaining=self.remaining_count,
            speed=self.speed
        )
        
        # Add control buttons
        from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        buttons = []
        if self.status == "running":
            buttons.append([
                InlineKeyboardButton(localization.get_text("btn_pause", self.lang), callback_data=f"bulk_pause_{self.chat_id}"),
                InlineKeyboardButton(localization.get_text("btn_stop", self.lang), callback_data=f"bulk_stop_{self.chat_id}")
            ])
        elif self.status == "paused":
            buttons.append([
                InlineKeyboardButton(localization.get_text("btn_resume", self.lang), callback_data=f"bulk_resume_{self.chat_id}"),
                InlineKeyboardButton(localization.get_text("btn_stop", self.lang), callback_data=f"bulk_stop_{self.chat_id}")
            ])
            
        buttons.append([
            InlineKeyboardButton(localization.get_text("btn_refresh", self.lang), callback_data=f"bulk_refresh_{self.chat_id}"),
            InlineKeyboardButton(localization.get_text("btn_back", self.lang), callback_data=f"chat_settings_{self.chat_id}")
        ])
        
        # Fetch the chat title from database to make the title nice
        chat_data = await database.get_chat(self.chat_id)
        chat_title = chat_data["chat_title"] if chat_data else str(self.chat_id)
        
        title_text = localization.get_text("bulk_status_title", self.lang, chat_title=chat_title)
        full_text = f"{title_text}\n\n{text}"
        
        try:
            await self.client.edit_message_text(
                chat_id=self.owner_id,
                message_id=self.progress_msg_id,
                text=full_text,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception as e:
            logger.error(f"Failed to update bulk progress message: {e}")

    async def run(self):
        """The main worker task for bulk approval."""
        try:
            peer = await self.client.resolve_peer(self.chat_id)
        except Exception as e:
            logger.error(f"Could not resolve peer for {self.chat_id}: {e}")
            self.status = "stopped"
            await self.update_status_msg(force=True)
            await database.save_bulk_job(self.chat_id, self.total_count, self.approved_count, self.failed_count, self.skipped_count, self.status)
            return

        offset_date = 0
        offset_user = raw.types.InputUserEmpty()
        
        # Retrieve the initial count of pending importers
        try:
            initial_req = await self.client.invoke(
                raw.functions.messages.GetChatInviteImporters(
                    peer=peer,
                    requested=True,
                    limit=1,
                    offset_date=0,
                    offset_user=raw.types.InputUserEmpty()
                )
            )
            self.total_count = initial_req.count
            self.remaining_count = self.total_count
            await database.save_bulk_job(self.chat_id, self.total_count, 0, 0, 0, "running")
            await self.update_status_msg(force=True)
        except Exception as e:
            logger.error(f"Error fetching initial invite importers count: {e}")
            self.status = "stopped"
            await self.update_status_msg(force=True)
            return

        # Fetch bulk approval speed setting from DB
        speed_setting = await database.get_setting("approval_speed", "160")
        try:
            req_per_min = int(speed_setting)
        except ValueError:
            req_per_min = 160
            
        sleep_between = 60.0 / max(1, req_per_min)
        
        logger.info(f"Starting bulk approval for chat {self.chat_id}. Total requests: {self.total_count}. Speed: {req_per_min}/min (sleep {sleep_between}s)")

        while self.status in ("running", "paused") and self.remaining_count > 0:
            # Check pause state
            if self.status == "paused":
                async with self.pause_cond:
                    await self.pause_cond.wait_for(lambda: self.status != "paused")
                # Update start time so speed calculation is not skewed by pause duration
                self.start_time = time.time() - ((self.approved_count + self.failed_count + self.skipped_count) / max(1, self.speed or 1) * 60)
                if self.status == "stopped":
                    break

            # Fetch a chunk of requests
            try:
                result = await self.client.invoke(
                    raw.functions.messages.GetChatInviteImporters(
                        peer=peer,
                        requested=True,
                        limit=50,
                        offset_date=offset_date,
                        offset_user=offset_user
                    )
                )
            except FloodWait as fw:
                logger.warning(f"FloodWait in GetChatInviteImporters: sleeping {fw.value}s")
                await asyncio.sleep(fw.value + 1)
                continue
            except Exception as e:
                logger.error(f"Error fetching chunk: {e}")
                self.status = "stopped"
                break

            if not result.importers:
                # No more importers
                break
                
            # Keep track of latest count in case it updated
            self.total_count = max(self.total_count, result.count)

            last_importer = None
            for importer in result.importers:
                # Store references for pagination offset
                last_importer = importer
                
                # Check running status inside loop
                if self.status != "running":
                    break
                    
                user_id = importer.user_id
                
                if user_id in self.skipped_user_ids:
                    continue

                # Process the approval
                approved_ok = False
                try:
                    await self.client.approve_chat_join_request(self.chat_id, user_id)
                    approved_ok = True
                    self.approved_count += 1
                    await database.increment_chat_approvals(self.chat_id)
                except FloodWait as fw:
                    logger.warning(f"FloodWait during approval: sleeping {fw.value}s")
                    # Put this user back or wait
                    await asyncio.sleep(fw.value + 2)
                    # Retry once
                    try:
                        await self.client.approve_chat_join_request(self.chat_id, user_id)
                        approved_ok = True
                        self.approved_count += 1
                        await database.increment_chat_approvals(self.chat_id)
                    except Exception as ex:
                        logger.error(f"Retry approval failed for {user_id}: {ex}")
                        self.failed_count += 1
                except RPCError as re:
                    # User cancelled request, chat not found, bot kicked, etc.
                    logger.warning(f"RPCError approving user {user_id}: {re}")
                    self.skipped_count += 1
                    self.skipped_user_ids.add(user_id)
                except Exception as ex:
                    logger.error(f"Unexpected error approving user {user_id}: {ex}")
                    self.failed_count += 1

                # Update database counts & memory remaining
                self.remaining_count = max(0, self.total_count - (self.approved_count + self.failed_count + self.skipped_count))
                
                # Save progress periodically to database
                await database.save_bulk_job(
                    self.chat_id, 
                    self.total_count, 
                    self.approved_count, 
                    self.failed_count, 
                    self.skipped_count, 
                    self.status
                )
                
                # Edit Telegram message (throttled)
                await self.update_status_msg()

                # Sleep to enforce approval speed limit
                await asyncio.sleep(sleep_between)

            # Paginate to next chunk if we still have items
            if last_importer and self.status == "running":
                offset_date = last_importer.date
                try:
                    offset_user = await self.client.resolve_peer(last_importer.user_id)
                except Exception:
                    # If resolving fails, we use default raw types empty user
                    offset_user = raw.types.InputUserEmpty()
            else:
                break

        # Finished or stopped
        if self.status == "running":
            self.status = "completed"
            
        self.remaining_count = 0
        await database.save_bulk_job(
            self.chat_id, 
            self.total_count, 
            self.approved_count, 
            self.failed_count, 
            self.skipped_count, 
            self.status
        )
        await self.update_status_msg(force=True)
        
        # Clean up database entry if completed
        if self.status == "completed":
            await database.delete_bulk_job(self.chat_id)
            
        # Remove from active jobs dict
        if self.chat_id in ACTIVE_BULK_JOBS:
            del ACTIVE_BULK_JOBS[self.chat_id]

async def start_bulk_job(client: Client, chat_id: int, owner_id: int, progress_msg_id: int, lang: str):
    """Starts a new bulk approval job."""
    # Stop any existing job for this chat first
    await stop_bulk_job(chat_id)
    
    job = BulkJob(client, chat_id, owner_id, progress_msg_id, lang)
    ACTIVE_BULK_JOBS[chat_id] = job
    
    # Run the worker task in the background
    job.task = asyncio.create_task(job.run())
    return job

async def pause_bulk_job(chat_id: int):
    """Pauses a running bulk job."""
    job = ACTIVE_BULK_JOBS.get(chat_id)
    if job and job.status == "running":
        job.status = "paused"
        await job.update_status_msg(force=True)
        await database.save_bulk_job(chat_id, job.total_count, job.approved_count, job.failed_count, job.skipped_count, "paused")

async def resume_bulk_job(chat_id: int):
    """Resumes a paused bulk job."""
    job = ACTIVE_BULK_JOBS.get(chat_id)
    if job and job.status == "paused":
        job.status = "running"
        async with job.pause_cond:
            job.pause_cond.notify_all()
        await job.update_status_msg(force=True)
        await database.save_bulk_job(chat_id, job.total_count, job.approved_count, job.failed_count, job.skipped_count, "running")

async def stop_bulk_job(chat_id: int):
    """Stops and cancels a bulk job."""
    job = ACTIVE_BULK_JOBS.get(chat_id)
    if job:
        job.status = "stopped"
        async with job.pause_cond:
            job.pause_cond.notify_all()
        if job.task:
            job.task.cancel()
        await job.update_status_msg(force=True)
        await database.save_bulk_job(chat_id, job.total_count, job.approved_count, job.failed_count, job.skipped_count, "stopped")
        if chat_id in ACTIVE_BULK_JOBS:
            del ACTIVE_BULK_JOBS[chat_id]
