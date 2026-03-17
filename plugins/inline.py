import logging
from pyrogram import Client, emoji, filters
from pyrogram.errors.exceptions.bad_request_400 import QueryIdInvalid
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultCachedDocument, InlineQuery
from database.ia_filterdb import get_search_results
from utils import is_req_subscribed, get_size, temp
from info import CACHE_TIME, AUTH_USERS, AUTH_CHANNEL, CUSTOM_FILE_CAPTION
from database.connections_mdb import active_connection

# 🔥 Fuzzy Search ke liye imports - AB YAHAN SE LENA HAI
from database.fuzzy_db import get_fuzzy_suggestions

logger = logging.getLogger(__name__)
cache_time = 0 if AUTH_USERS or AUTH_CHANNEL else CACHE_TIME

async def inline_users(query: InlineQuery):
    if AUTH_USERS:
        if query.from_user and query.from_user.id in AUTH_USERS:
            return True
        else:
            return False
    if query.from_user and query.from_user.id not in temp.BANNED_USERS:
        return True
    return False

@Client.on_inline_query()
async def answer(bot, query):
    """Show search results for given inline query"""
    chat_id = await active_connection(str(query.from_user.id))
    
    if not await inline_users(query):
        await query.answer(results=[],
                           cache_time=0,
                           switch_pm_text='okDa',
                           switch_pm_parameter="hehe")
        return

    if AUTH_CHANNEL and not await is_req_subscribed(bot, query):
        await query.answer(results=[],
                           cache_time=0,
                           switch_pm_text='You have to subscribe my channel to use the bot',
                           switch_pm_parameter="subscribe")
        return

    results = []
    if '|' in query.query:
        string, file_type = query.query.split('|', maxsplit=1)
        string = string.strip()
        file_type = file_type.strip().lower()
    else:
        string = query.query.strip()
        file_type = None

    offset = int(query.offset or 0)
    reply_markup = get_reply_markup(query=string)
    files, next_offset, total = await get_search_results(
                                                  chat_id,
                                                  string,
                                                  file_type=file_type,
                                                  max_results=10,
                                                  offset=offset)

    # ✅ अगर files मिलीं तो normal results दिखाओ
    if total > 0:
        for file in files:
            title=file.file_name
            size=get_size(file.file_size)
            f_caption=file.caption
            if CUSTOM_FILE_CAPTION:
                try:
                    f_caption=CUSTOM_FILE_CAPTION.format(file_name= '' if title is None else title, file_size='' if size is None else size, file_caption='' if f_caption is None else f_caption)
                except Exception as e:
                    logger.exception(e)
                    f_caption=f_caption
            if f_caption is None:
                f_caption = f"{file.file_name}"
            results.append(
                InlineQueryResultCachedDocument(
                    title=file.file_name,
                    document_file_id=file.file_id,
                    caption=f_caption,
                    description=f'Size: {get_size(file.file_size)}\nType: {file.file_type}',
                    reply_markup=reply_markup))

        if results:
            switch_pm_text = f"{emoji.FILE_FOLDER} Results - {total}"
            if string:
                switch_pm_text += f" for {string}"
            try:
                await query.answer(results=results,
                               is_personal = True,
                               cache_time=cache_time,
                               switch_pm_text=switch_pm_text,
                               switch_pm_parameter="start",
                               next_offset=str(next_offset))
            except QueryIdInvalid:
                pass
            except Exception as e:
                logging.exception(str(e))
    
    # 🔥 यहाँ बड़ा बदलाव - अब No Results की जगह Fuzzy Suggestions दिखेंगी
    else:
        # Fuzzy suggestions लो
        suggestions = await get_fuzzy_suggestions(string, limit=5, score_cutoff=50)
        
        if suggestions:
            # Suggestions मिलीं तो उन्हें दिखाओ
            switch_pm_text = f"🔍 Did you mean?"
            
            # Suggestions को formatted text में बदलो
            suggestion_text = f"{emoji.CROSS_MARK} No exact results for '{string}'\n\n"
            suggestion_text += "🔎 **Did you mean one of these?**\n\n"
            
            for idx, sug in enumerate(suggestions, 1):
                suggestion_text += f"{idx}. {sug['name']}\n"
            
            await query.answer(results=[],
                               is_personal=True,
                               cache_time=0,
                               switch_pm_text=suggestion_text[:50] + "...",
                               switch_pm_parameter="fuzzy_suggestions")
        else:
            # ना files मिलीं ना suggestions
            switch_pm_text = f'{emoji.CROSS_MARK} No results'
            if string:
                switch_pm_text += f' for "{string}"'

            await query.answer(results=[],
                               is_personal = True,
                               cache_time=cache_time,
                               switch_pm_text=switch_pm_text,
                               switch_pm_parameter="okay")


def get_reply_markup(query):
    buttons = [
        [
            InlineKeyboardButton('Search again', switch_inline_query_current_chat=query)
        ]
        ]
    return InlineKeyboardMarkup(buttons)


# 🔥 Optional: Fuzzy suggestions के लिए अलग handler
@Client.on_callback_query(filters.regex(r'^fuzzy_'))
async def fuzzy_callback(bot, callback_query):
    """Handle fuzzy suggestion clicks"""
    from database.ia_filterdb import get_search_results
    
    query = callback_query.data.replace('fuzzy_', '')
    
    await callback_query.answer()
    
    # User को बताओ कि search हो रहा है
    await callback_query.edit_message_text(
        f"🔍 Searching for: {query}..."
    )
    
    # Ab is query से normal search karo
    chat_id = callback_query.message.chat.id
    files, _, total = await get_search_results(chat_id, query)
    
    if total > 0:
        # Files मिल गईं
        text = f"✅ Found {total} results for '{query}'!\n"
        text += "Use inline mode to search normally."
        await callback_query.edit_message_text(text)
    else:
        # फिर भी नहीं मिली
        await callback_query.edit_message_text(
            f"❌ Sorry, still no results found for '{query}'\n"
            f"Try different keywords."
        )