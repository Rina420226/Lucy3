import os
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import Config

logger = logging.getLogger(__name__)

# IMDb status
IMDB_ENABLED = getattr(Config, 'IMDB', False)

if IMDB_ENABLED:
    try:
        from IMDBKit import IMDB
        imdb = IMDB()
        logger.info("✅ IMDb Kit imported successfully!")
    except ImportError:
        IMDB_ENABLED = False
        logger.error("❌ IMDBKit not installed! Run: pip install git+https://github.com/NBBotz/IMDBKit")
else:
    logger.info("ℹ️ IMDb features are disabled in config")

@Client.on_message(filters.command("imdb") & filters.private)
async def imdb_search(client, message):
    """Search movie and show poster"""
    if not IMDB_ENABLED:
        await message.reply_text(
            "❌ **IMDb features are disabled!**\n\n"
            "Contact developer to enable this feature."
        )
        return
    
    # Get movie name
    query = " ".join(message.command[1:])
    if not query:
        await message.reply_text(
            "**Usage:** `/imdb <movie name>`\n"
            "Example: `/imdb Inception`"
        )
        return
    
    # Send typing action
    await message.reply_chat_action("typing")
    
    try:
        # Search movie
        results = await imdb.search(query)
        
        if not results:
            await message.reply_text(f"❌ No results found for: **{query}**")
            return
        
        # Get first result details
        movie = results[0]
        movie_id = movie['id']
        
        await message.reply_text(f"🔍 Fetching details for **{movie['title']}**...")
        
        details = await imdb.get_movie(movie_id)
        
        if not details:
            await message.reply_text("❌ Could not fetch movie details!")
            return
        
        # Get template from config or use default
        template = getattr(Config, 'IMDB_TEMPLATE', 
            "**🎬 Title:** {title}\n"
            "**📊 Rating:** {rating}/10 ⭐\n"
            "**📅 Year:** {year}\n"
            "**🎭 Genres:** {genres}\n"
            "**🌍 Languages:** {languages}\n"
            "**⏱️ Runtime:** {runtime} mins\n"
            "**📝 Plot:** {plot}\n\n"
            "**🎥 Cast:** {cast}\n"
            "**🎬 Director:** {director}\n\n"
            "🔗 **IMDb Link:** https://www.imdb.com/title/{imdb_id}/"
        )
        
        # Format template
        movie_info = template.format(
            title=details.get('title', 'N/A'),
            rating=details.get('rating', 'N/A'),
            year=details.get('year', 'N/A'),
            genres=', '.join(details.get('genres', ['N/A'])),
            languages=', '.join(details.get('languages', ['N/A'])),
            runtime=details.get('runtime', 'N/A'),
            plot=details.get('plot', 'No plot available.'),
            cast=', '.join([c['name'] for c in details.get('cast', [])[:5]]),
            director=', '.join([d['name'] for d in details.get('directors', [])]),
            imdb_id=details.get('imdb_id', 'N/A')
        )
        
        # Get poster URL
        poster_url = details.get('poster', '')
        
        # Reply with poster if available
        if poster_url:
            try:
                await message.reply_photo(
                    photo=poster_url,
                    caption=movie_info,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            "🔗 View on IMDb", 
                            url=f"https://www.imdb.com/title/{details.get('imdb_id', '')}/"
                        )
                    ]])
                )
            except Exception as e:
                logger.error(f"Poster send failed: {e}")
                await message.reply_text(
                    movie_info,
                    disable_web_page_preview=True,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            "🔗 View on IMDb", 
                            url=f"https://www.imdb.com/title/{details.get('imdb_id', '')}/"
                        )
                    ]])
                )
        else:
            await message.reply_text(
                movie_info,
                disable_web_page_preview=True,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "🔗 View on IMDb", 
                        url=f"https://www.imdb.com/title/{details.get('imdb_id', '')}/"
                    )
                ]])
            )
            
    except Exception as e:
        logger.error(f"IMDb search error: {e}")
        await message.reply_text(f"❌ Error: {str(e)}")

@Client.on_message(filters.command("imdb_status"))
async def imdb_status(client, message):
    """Check IMDb status"""
    status = "✅ **Enabled**" if IMDB_ENABLED else "❌ **Disabled**"
    await message.reply_text(
        f"**📊 IMDb Feature Status:**\n\n"
        f"{status}\n\n"
        f"**Commands:**\n"
        f"• `/imdb <movie>` - Search movie\n"
        f"{'' if IMDB_ENABLED else '⚠️ Contact developer to enable this feature.'}"
    )
