from pyrogram import Client, filters

@Client.on_message(filters.command("rename") & filters.reply)
async def rename_file(client, message):
    try:
        replied = message.reply_to_message
        
        if not replied.media:
            return await message.reply_text("❌ Reply to a file")

        if len(message.command) < 2:
            return await message.reply_text("❌ Give new name\nExample: /rename Movie.mkv")

        new_name = message.text.split(" ", 1)[1]

        await message.reply_text("⏳ Renaming...")

        await replied.copy(
            chat_id=message.chat.id,
            caption=f"📂 {new_name}"
        )

        await message.reply_text("✅ Renamed Successfully")

    except Exception as e:
        await message.reply_text(f"Error: {e}")