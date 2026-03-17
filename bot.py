import sys
import glob
import importlib
from pathlib import Path
from pyrogram import Client, idle, __version__
from pyrogram.raw.all import layer
import logging
import logging.config
import time
import asyncio
from datetime import date, datetime
import pytz
from aiohttp import web

from database.ia_filterdb import Media, Media2, choose_mediaDB, tempDict, db as clientDB
from database.users_chats_db import db
from info import *
from utils import temp
from Script import script
from plugins import web_server, check_expired_premium
from LucyBot.Bot import Codeflix
from LucyBot.util.keepalive import ping_server
from LucyBot.Bot.clients import initialize_clients

# 🔥 Fuzzy Search ke liye imports
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database.ia_filterdb import get_search_results, get_file_details

logging.config.fileConfig('logging.conf')
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("imdbpy").setLevel(logging.ERROR)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("aiohttp").setLevel(logging.ERROR)
logging.getLogger("aiohttp.web").setLevel(logging.ERROR)

botStartTime = time.time()
ppath = "plugins/*.py"
files = glob.glob(ppath)

async def Lucy_start():
    print('\n')
    print('\nInitalizing Lucy')
    await Codeflix.start()
    bot_info = await Codeflix.get_me()
    Codeflix.username = bot_info.username
    await initialize_clients()
    for name in files:
        with open(name) as a:
            patt = Path(a.name)
            plugin_name = patt.stem.replace(".py", "")
            plugins_dir = Path(f"plugins/{plugin_name}.py")
            import_path = "plugins.{}".format(plugin_name)
            spec = importlib.util.spec_from_file_location(import_path, plugins_dir)
            load = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(load)
            sys.modules["plugins." + plugin_name] = load
            print("Lucy Bot Imported => " + plugin_name)
    if ON_HEROKU:
        asyncio.create_task(ping_server()) 
    b_users, b_chats = await db.get_banned()
    temp.BANNED_USERS = b_users
    temp.BANNED_CHATS = b_chats
    await Media.ensure_indexes()
    await Media2.ensure_indexes()
    stats = await clientDB.command('dbStats')
    free_dbSize = round(512-((stats['dataSize']/(1024*1024))+(stats['indexSize']/(1024*1024))), 2)
    if DATABASE_URI2 and free_dbSize<62: #if the primary db have less than 62MB left, use second DB.
        tempDict["indexDB"] = DATABASE_URI2
        logging.info(f"Since Primary DB have only {free_dbSize} MB left, Secondary DB will be used to store datas.")
    elif DATABASE_URI2 is None:
        logging.error("Missing second DB URI !\n\nAdd SECONDDB_URI now !\n\nExiting...")
        exit()
    else:
        logging.info(f"Since primary DB have enough space ({free_dbSize}MB) left, It will be used for storing datas.")
    await choose_mediaDB()    
    me = await Codeflix.get_me()
    temp.ME = me.id
    temp.U_NAME = me.username
    temp.B_NAME = me.first_name
    temp.B_LINK = me.mention
    Codeflix.username = '@' + me.username
    Codeflix.loop.create_task(check_expired_premium(Codeflix))
    logging.info(f"{me.first_name} with Pyrogram v{__version__} (Layer {layer}) started on {me.username}.")
    logging.info(LOG_STR)
    logging.info(script.LOGO)
    tz = pytz.timezone('Asia/Kolkata')
    today = date.today()
    now = datetime.now(tz)
    time = now.strftime("%H:%M:%S %p")
    await Codeflix.send_message(chat_id=LOG_CHANNEL, text=script.RESTART_TXT.format(temp.B_LINK, today, time))
    app = web.AppRunner(await web_server())
    await app.setup()
    bind_address = "0.0.0.0"
    await web.TCPSite(app, bind_address, PORT).start()
    await idle()
    

# ========== 🔥 NEW CALLBACK HANDLER FOR FUZZY SUGGESTIONS ==========

@Codeflix.on_callback_query()
async def callback_handlers(client, callback_query):
    """Handle all callback queries including fuzzy suggestions"""
    
    data = callback_query.data
    user_id = callback_query.from_user.id
    
    # ✅ Fuzzy suggestion click handler
    if data.startswith("fuzzy_"):
        # "fuzzy_" ke baad ka part actual file name hai
        file_name = data.replace("fuzzy_", "", 1)
        
        await callback_query.answer(f"🔍 Searching for: {file_name[:30]}...")
        
        # User ko batayein ki search ho rahi hai
        await callback_query.edit_message_text(
            f"🔍 **Searching for:** `{file_name}`\n\nPlease wait..."
        )
        
        # Ab is file name से database में search karein
        # Note: exact file name se search kar rahe hain
        chat_id = callback_query.message.chat.id
        files, _, total = await get_search_results(chat_id, file_name)
        
        if total > 0:
            # Files mil gayi - pehli file details lein
            file = files[0]
            file_id = file.file_id
            file_caption = file.caption or file.file_name
            
            # File send karein
            await client.send_document(
                chat_id=callback_query.from_user.id,
                document=file_id,
                caption=f"**{file_name}**\n\n✅ Found in database!"
            )
            
            # Callback message update karein
            await callback_query.edit_message_text(
                f"✅ **Found {total} result(s) for:** `{file_name}`\n\n"
                f"📤 File has been sent to you in PM!"
            )
        else:
            # Agar kisi wajah se file na mile (should not happen, but just in case)
            await callback_query.edit_message_text(
                f"❌ **Sorry, couldn't find the file:** `{file_name}`\n\n"
                f"Please try searching with different keywords."
            )
    
    # ✅ Cancel handler
    elif data == "fuzzy_cancel":
        await callback_query.answer("Cancelled")
        await callback_query.message.delete()
    
    # ✅ Agar koi aur callback hai to usko original handlers ke liye pass-through
    # Note: Aapke original callback handlers (like delallconfirm etc) ko ye override nahi karega
    # Kyunki wo specific patterns handle karte hain, aur ye sirf fuzzy_ prefix handle kar raha hai


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(Lucy_start())
    except KeyboardInterrupt:
        logging.info('Service Stopped Bye 👋')