import os
import math
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from PyAniDL import Search, downloader

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

app = Client("ani_pro_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
search_db = {}

@app.on_message(filters.command("search"))
async def search_anime(client, message):
    query = " ".join(message.command[1:])
    if not query:
        return await message.reply_text("❓ Naam toh likho bhai!")

    status = await message.reply_text("🔍 **Searching on Multiple Servers...**")
    
    try:
        # Try 1: Search with original query
        s = Search(query, provider='gogoanime')
        results = s.get_results()

        # Try 2: Agar result nahi mila, toh 'Hindi' word hata kar search karo
        if not results and "Hindi" in query:
            await status.edit("⚠️ Hindi version nahi mila, English/Original dhoondh raha hoon...")
            clean_query = query.replace("Hindi", "").strip()
            s = Search(clean_query, provider='gogoanime')
            results = s.get_results()

        if not results:
            return await status.edit("❌ **Abhi bhi kuch nahi mila!**\n\nSpelling check karo ya koi doosra anime try karo.")

        # Progress bar animation (Visual only)
        await status.edit("✅ Result Mil Gaya!\n[████████░░] 80%\nExtracting Links...")
        
        anime = results[0]
        # Yahan hum link extract karne ki koshish kar rahe hain
        try:
            dl = downloader.Downloader(anime.get('url'))
            links = dl.get_links(quality='720p')
        except:
            # Agar 720p fail ho toh 480p try karo
            links = dl.get_links(quality='480p')

        if not links:
            return await status.edit("❌ **Server Busy:** Links extract nahi ho pa rahe. Thodi der baad try karein.")

        chat_id = message.chat.id
        search_db[chat_id] = {"title": anime.get('title'), "links": links}
        await show_episodes(client, chat_id, status.id, page=1)

    except Exception as e:
        print(f"Error: {e}")
        await status.edit(f"⚠️ **Technical Error:** Scraping block ho gayi hai. Railway ka IP change karein.")

# ... (show_episodes aur handle_pagination wala purana code yahan rahega)
app.run()
