import io
import logging
import re
from pyrogram import filters, Client, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from pyrogram.errors import FloodWait
import asyncio

from database.filters_mdb import (
    add_filter,
    get_filters,
    delete_filter,
    count_filters
)
from database.connections_mdb import active_connection
from database.ia_filterdb import get_search_results, get_file_details
from database.fuzzy_db import get_fuzzy_suggestions
from utils import get_file_id, parser, split_quotes, get_size, get_settings, save_group_settings, temp
from info import ADMINS, CUSTOM_FILE_CAPTION, PROTECT_CONTENT

logger = logging.getLogger(__name__)

# ========================================================
# EXISTING FILTER COMMANDS (Original Code)
# ========================================================

@Client.on_message(filters.command(['filter', 'add']) & filters.incoming)
async def addfilter(client, message):
    userid = message.from_user.id if message.from_user else None
    if not userid:
        return await message.reply(f"You are anonymous admin. Use /connect {message.chat.id} in PM")
    chat_type = message.chat.type
    args = message.text.html.split(None, 1)

    if chat_type == enums.ChatType.PRIVATE:
        grpid = await active_connection(str(userid))
        if grpid is not None:
            grp_id = grpid
            try:
                chat = await client.get_chat(grpid)
                title = chat.title
            except:
                await message.reply_text("Make sure I'm present in your group!!", quote=True)
                return
        else:
            await message.reply_text("I'm not connected to any groups!", quote=True)
            return

    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grp_id = message.chat.id
        title = message.chat.title

    else:
        return

    st = await client.get_chat_member(grp_id, userid)
    if (
        st.status != enums.ChatMemberStatus.ADMINISTRATOR
        and st.status != enums.ChatMemberStatus.OWNER
        and str(userid) not in ADMINS
    ):
        return

    if len(args) < 2:
        await message.reply_text("Command Incomplete :(", quote=True)
        return

    extracted = split_quotes(args[1])
    text = extracted[0].lower()

    if not message.reply_to_message and len(extracted) < 2:
        await message.reply_text("Add some content to save your filter!", quote=True)
        return

    if (len(extracted) >= 2) and not message.reply_to_message:
        reply_text, btn, alert = parser(extracted[1], text)
        fileid = None
        if not reply_text:
            await message.reply_text("You cannot have buttons alone, give some text to go with it!", quote=True)
            return

    elif message.reply_to_message and message.reply_to_message.reply_markup:
        try:
            rm = message.reply_to_message.reply_markup
            btn = rm.inline_keyboard
            msg = get_file_id(message.reply_to_message)
            if msg:
                fileid = msg.file_id
                reply_text = message.reply_to_message.caption.html
            else:
                reply_text = message.reply_to_message.text.html
                fileid = None
            alert = None
        except:
            reply_text = ""
            btn = "[]" 
            fileid = None
            alert = None

    elif message.reply_to_message and message.reply_to_message.media:
        try:
            msg = get_file_id(message.reply_to_message)
            fileid = msg.file_id if msg else None
            reply_text, btn, alert = parser(extracted[1], text) if message.reply_to_message.sticker else parser(message.reply_to_message.caption.html, text)
        except:
            reply_text = ""
            btn = "[]"
            alert = None
    elif message.reply_to_message and message.reply_to_message.text:
        try:
            fileid = None
            reply_text, btn, alert = parser(message.reply_to_message.text.html, text)
        except:
            reply_text = ""
            btn = "[]"
            alert = None
    else:
        return

    await add_filter(grp_id, text, reply_text, btn, fileid, alert)

    await message.reply_text(
        f"Filter for  `{text}`  added in  **{title}**",
        quote=True,
        parse_mode=enums.ParseMode.MARKDOWN
    )


@Client.on_message(filters.command(['viewfilters', 'filters']) & filters.incoming)
async def get_all(client, message):
    
    chat_type = message.chat.type
    userid = message.from_user.id if message.from_user else None
    if not userid:
        return await message.reply(f"You are anonymous admin. Use /connect {message.chat.id} in PM")
    if chat_type == enums.ChatType.PRIVATE:
        userid = message.from_user.id
        grpid = await active_connection(str(userid))
        if grpid is not None:
            grp_id = grpid
            try:
                chat = await client.get_chat(grpid)
                title = chat.title
            except:
                await message.reply_text("Make sure I'm present in your group!!", quote=True)
                return
        else:
            await message.reply_text("I'm not connected to any groups!", quote=True)
            return

    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grp_id = message.chat.id
        title = message.chat.title

    else:
        return

    st = await client.get_chat_member(grp_id, userid)
    if (
        st.status != enums.ChatMemberStatus.ADMINISTRATOR
        and st.status != enums.ChatMemberStatus.OWNER
        and str(userid) not in ADMINS
    ):
        return

    texts = await get_filters(grp_id)
    count = await count_filters(grp_id)
    if count:
        filterlist = f"Total number of filters in **{title}** : {count}\n\n"

        for text in texts:
            keywords = " ×  `{}`\n".format(text)

            filterlist += keywords

        if len(filterlist) > 4096:
            with io.BytesIO(str.encode(filterlist.replace("`", ""))) as keyword_file:
                keyword_file.name = "keywords.txt"
                await message.reply_document(
                    document=keyword_file,
                    quote=True
                )
            return
    else:
        filterlist = f"There are no active filters in **{title}**"

    await message.reply_text(
        text=filterlist,
        quote=True,
        parse_mode=enums.ParseMode.MARKDOWN
    )
        

@Client.on_message(filters.command('del') & filters.incoming)
async def deletefilter(client, message):
    userid = message.from_user.id if message.from_user else None
    if not userid:
        return await message.reply(f"You are anonymous admin. Use /connect {message.chat.id} in PM")
    chat_type = message.chat.type

    if chat_type == enums.ChatType.PRIVATE:
        grpid  = await active_connection(str(userid))
        if grpid is not None:
            grp_id = grpid
            try:
                chat = await client.get_chat(grpid)
                title = chat.title
            except:
                await message.reply_text("Make sure I'm present in your group!!", quote=True)
                return
        else:
            await message.reply_text("I'm not connected to any groups!", quote=True)

    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grp_id = message.chat.id
        title = message.chat.title

    else:
        return

    st = await client.get_chat_member(grp_id, userid)
    if (
        st.status != enums.ChatMemberStatus.ADMINISTRATOR
        and st.status != enums.ChatMemberStatus.OWNER
        and str(userid) not in ADMINS
    ):
        return

    try:
        cmd, text = message.text.split(" ", 1)
    except:
        await message.reply_text(
            "<i>Mention the filtername which you wanna delete!</i>\n\n"
            "<code>/del filtername</code>\n\n"
            "Use /viewfilters to view all available filters",
            quote=True
        )
        return

    query = text.lower()

    await delete_filter(message, query, grp_id)
        

@Client.on_message(filters.command('delall') & filters.incoming)
async def delallconfirm(client, message):
    userid = message.from_user.id if message.from_user else None
    if not userid:
        return await message.reply(f"You are anonymous admin. Use /connect {message.chat.id} in PM")
    chat_type = message.chat.type

    if chat_type == enums.ChatType.PRIVATE:
        grpid  = await active_connection(str(userid))
        if grpid is not None:
            grp_id = grpid
            try:
                chat = await client.get_chat(grpid)
                title = chat.title
            except:
                await message.reply_text("Make sure I'm present in your group!!", quote=True)
                return
        else:
            await message.reply_text("I'm not connected to any groups!", quote=True)
            return

    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grp_id = message.chat.id
        title = message.chat.title

    else:
        return

    st = await client.get_chat_member(grp_id, userid)
    if (st.status == enums.ChatMemberStatus.OWNER) or (str(userid) in ADMINS):
        await message.reply_text(
            f"This will delete all filters from '{title}'.\nDo you want to continue??",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(text="YES",callback_data="delallconfirm")],
                [InlineKeyboardButton(text="CANCEL",callback_data="delallcancel")]
            ]),
            quote=True
        )


# ========================================================
# MAIN AUTO FILTER WITH FUZZY SUGGESTIONS
# ========================================================

@Client.on_message(filters.text & filters.group & ~filters.command([
    'start', 'help', 'settings', 'filter', 'add', 'del', 'delall', 
    'viewfilters', 'filters', 'connect', 'disconnect', 'connections',
    'stats', 'info', 'id', 'shortlink', 'plan', 'myplan'
]))
async def auto_filter(client: Client, message: Message):
    """
    Main auto filter function with fuzzy suggestions
    """
    # Basic checks
    if not message.from_user:
        return
    
    query = message.text.strip()
    if len(query) < 2:
        return
    
    # Check if user is banned
    if message.from_user.id in temp.BANNED_USERS:
        return
    
    logger.info(f"🔍 Search query: {query} from {message.from_user.first_name}")
    
    try:
        # First try normal search
        files, next_offset, total_results = await get_search_results(
            message.chat.id,
            query,
            max_results=10,
            offset=0
        )
        
        if total_results > 0:
            # Results found - send them
            await send_results(client, message, files, total_results, query)
            return
        
        # No results found - try fuzzy suggestions
        await send_fuzzy_suggestions(client, message, query)
        
    except Exception as e:
        logger.error(f"Error in auto_filter: {e}")
        await message.reply_text(
            "❌ An error occurred while searching. Please try again later.",
            quote=True
        )


async def send_fuzzy_suggestions(client, message, query):
    """
    Send fuzzy search suggestions when no results found
    """
    # Show typing indicator
    await client.send_chat_action(message.chat.id, "typing")
    
    # Get fuzzy suggestions
    suggestions = await get_fuzzy_suggestions(query, limit=5, score_cutoff=50)
    
    if not suggestions:
        # No suggestions found
        await message.reply_text(
            f"❌ **No results found for:** `{query}`\n\n"
            f"💡 Try different keywords or check spelling.",
            quote=True
        )
        return
    
    # Create suggestion message
    text = f"❌ **No exact results for:** `{query}`\n\n"
    text += "🔎 **Did you mean one of these?**\n"
    text += "Click a suggestion to search:\n\n"
    
    # Create buttons for each suggestion
    buttons = []
    for sug in suggestions:
        display_name = sug['display'][:40] + "..." if len(sug['display']) > 40 else sug['display']
        buttons.append([
            InlineKeyboardButton(
                f"📌 {display_name}",
                callback_data=f"fuzzy_{sug['name']}"
            )
        ])
    
    # Add cancel button
    buttons.append([
        InlineKeyboardButton("❌ Cancel", callback_data="fuzzy_cancel")
    ])
    
    reply_markup = InlineKeyboardMarkup(buttons)
    
    await message.reply_text(
        text,
        reply_markup=reply_markup,
        quote=True
    )


async def send_results(client, message, files, total_results, query):
    """
    Send search results to user
    """
    try:
        # Prepare result message
        if total_results > 5:
            result_text = f"✅ **Found {total_results} results for:** `{query}`\n\n"
            result_text += f"**Showing first 5 results:**\n\n"
            files_to_show = files[:5]
        else:
            result_text = f"✅ **Found {total_results} results for:** `{query}`\n\n"
            files_to_show = files
        
        # Create buttons for each file
        buttons = []
        for file in files_to_show:
            file_name = file.file_name
            file_size = get_size(file.file_size)
            
            # Shorten filename if too long
            display_name = file_name[:35] + "..." if len(file_name) > 35 else file_name
            
            buttons.append([
                InlineKeyboardButton(
                    f"📄 {display_name} ({file_size})",
                    callback_data=f"file_{file.file_id}"
                )
            ])
        
        # Add more options button if there are more results
        if total_results > 5:
            buttons.append([
                InlineKeyboardButton(
                    f"📚 View All {total_results} Results",
                    callback_data=f"viewall_{query}"
                )
            ])
        
        # Add search again button
        buttons.append([
            InlineKeyboardButton("🔍 Search Again", switch_inline_query_current_chat=query)
        ])
        
        reply_markup = InlineKeyboardMarkup(buttons)
        
        await message.reply_text(
            result_text,
            reply_markup=reply_markup,
            quote=True
        )
        
    except Exception as e:
        logger.error(f"Error in send_results: {e}")
        await message.reply_text(
            f"✅ Found {total_results} results for: {query}\n"
            f"Use inline mode to get files.",
            quote=True
        )


# ========================================================
# CALLBACK HANDLERS
# ========================================================

@Client.on_callback_query(filters.regex(r'^file_'))
async def file_callback(client, callback_query):
    """Handle file button clicks"""
    file_id = callback_query.data.replace('file_', '')
    
    try:
        # Get file details
        files = await get_file_details(file_id)
        if not files:
            await callback_query.answer("File not found!", show_alert=True)
            return
        
        file = files[0]
        
        # Prepare caption
        caption = file.caption or file.file_name
        if CUSTOM_FILE_CAPTION:
            try:
                caption = CUSTOM_FILE_CAPTION.format(
                    file_name=file.file_name,
                    file_size=get_size(file.file_size),
                    file_caption=caption
                )
            except:
                pass
        
        # Send file
        await callback_query.message.reply_document(
            document=file.file_id,
            caption=caption,
            protect_content=PROTECT_CONTENT
        )
        
        await callback_query.answer("File sent successfully!")
        
    except Exception as e:
        logger.error(f"Error in file_callback: {e}")
        await callback_query.answer("Error sending file!", show_alert=True)


@Client.on_callback_query(filters.regex(r'^fuzzy_'))
async def fuzzy_callback(client, callback_query):
    """Handle fuzzy suggestion clicks"""
    query = callback_query.data.replace('fuzzy_', '')
    
    await callback_query.answer(f"Searching for: {query[:30]}...")
    
    # Search with the suggested name
    files, _, total = await get_search_results(
        callback_query.message.chat.id,
        query,
        max_results=10,
        offset=0
    )
    
    if total > 0:
        await send_results(client, callback_query.message, files, total, query)
        await callback_query.message.delete()
    else:
        await callback_query.message.edit_text(
            f"❌ No results found for: {query}"
        )


@Client.on_callback_query(filters.regex(r'^fuzzy_cancel$'))
async def fuzzy_cancel_callback(client, callback_query):
    """Handle cancel button"""
    await callback_query.answer("Cancelled")
    await callback_query.message.delete()


@Client.on_callback_query(filters.regex(r'^viewall_'))
async def viewall_callback(client, callback_query):
    """Handle view all results button"""
    query = callback_query.data.replace('viewall_', '')
    
    await callback_query.answer()
    await callback_query.message.reply_text(
        f"🔍 Please use inline mode to view all results for: {query}\n\n"
        f"Type @{client.me.username} {query} in any chat.",
        quote=True
    )


@Client.on_callback_query(filters.regex(r'^delallconfirm$'))
async def delallconfirm_callback(client, callback_query):
    """Handle delete all confirmation"""
    await callback_query.answer()
    await callback_query.message.edit_text("✅ All filters deleted!")