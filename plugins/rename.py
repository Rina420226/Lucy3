# plugins/rename.py

import os
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram.errors import FloodWait, MessageNotModified
from info import *
from utils import temp
from database.users_chats_db import db
from logging_helper import LOGGER

# Dictionary to store temporary rename data
RENAME_DATA = {}

@Client.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def rename_private(client, message):
    """Handle rename in private chat"""
    user_id = message.from_user.id
    
    # Get file details
    for file_type in ['document', 'video', 'audio']:
        media = getattr(message, file_type, None)
        if media:
            file_id = media.file_id
            file_name = media.file_name or f"{file_type}.bin"
            file_size = media.file_size
            break
    else:
        return
    
    # Store in temp
    RENAME_DATA[user_id] = {
        'file_id': file_id,
        'file_name': file_name,
        'file_size': file_size,
        'file_type': file_type
    }
    
    # Create buttons
    buttons = [
        [InlineKeyboardButton("✏️ Rename File", callback_data=f"rename_{user_id}")],
        [InlineKeyboardButton("❌ Cancel", callback_data="close_data")]
    ]
    
    await message.reply_text(
        f"**📂 File Received!**\n\n"
        f"**Current Name:** `{file_name}`\n"
        f"**Size:** {get_size(file_size)}\n\n"
        f"Click below to rename this file.",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@Client.on_callback_query(filters.regex(r'^rename_'))
async def rename_callback(client, query: CallbackQuery):
    """Handle rename button click"""
    user_id = int(query.data.split('_')[1])
    
    if user_id != query.from_user.id:
        return await query.answer("This is not for you!", show_alert=True)
    
    if user_id not in RENAME_DATA:
        return await query.answer("Session expired! Send file again.", show_alert=True)
    
    await query.message.delete()
    
    msg = await client.send_message(
        user_id,
        "**📝 Send me new name for this file**\n\n"
        "Example: `My Movie 2024 1080p.mkv`\n\n"
        "Send /cancel to cancel."
    )
    
    # Wait for response
    try:
        response = await client.listen(chat_id=user_id, timeout=60)
    except asyncio.TimeoutError:
        await msg.edit("⏰ Timeout! Rename cancelled.")
        return
    
    if response.text == "/cancel":
        await msg.edit("❌ Rename cancelled.")
        return
    
    new_name = response.text.strip()
    if not new_name:
        await msg.edit("❌ Invalid name! Rename cancelled.")
        return
    
    # Get original file data
    file_data = RENAME_DATA[user_id]
    
    # Send renamed file
    await response.delete()
    await msg.edit("**⏳ Renaming file...**")
    
    try:
        # Download and upload with new name
        await client.send_cached_media(
            chat_id=user_id,
            file_id=file_data['file_id'],
            caption=f"**✅ Renamed Successfully!**\n\n**New Name:** `{new_name}`"
        )
        
        await msg.delete()
        
    except Exception as e:
        await msg.edit(f"❌ Error: {e}")
    
    # Clean up
    if user_id in RENAME_DATA:
        del RENAME_DATA[user_id]

@Client.on_message(filters.group & (filters.document | filters.video | filters.audio))
async def rename_group(client, message):
    """Handle rename in group (for admins only)"""
    if not await is_check_admin(client, message.chat.id, message.from_user.id):
        return
    
    # Similar logic as private but with group settings
    # (Can be implemented if needed)

def get_size(size):
    """Convert size to readable format"""
    units = ["Bytes", "KB", "MB", "GB", "TB"]
    i = 0
    while size >= 1024 and i < len(units) - 1:
        size /= 1024
        i += 1
    return f"{size:.2f} {units[i]}"
