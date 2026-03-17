import os
import math
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from PyAniDL import Search, downloader

# API Details
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

app = Client("ani_pro_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# In-memory storage for pagination (Real bot mein database use karna chahiye)
search_db = {}

def get_progress_bar(current, total):
    percentage = current / total
    completed = int(percentage * 10)
    remaining = 10 - completed
    p_bar = "✅" * completed + "⬜" * remaining
    return f"[{p_bar}] {round(percentage * 100)}%"

@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text(f"🔥 **Anime Downloader Pro**\n\nBhai, anime ka naam likho aur main direct download links nikal dunga.\n\nUsage: `/search Naruto Hindi`")

@app.on_message(filters.command("search"))
async def search_anime(client, message):
    query = " ".join(message.command[1:])
    if not query:
        return await message.reply_text("❓ Naam toh likho bhai!")

    status = await message.reply_text("🔍 **Initialising Search...**")
    
    try:
        # Progress Bar Simulation 1
        await status.edit(f"🔍 Searching: `{query}`\n{get_progress_bar(30, 100)}")
        
        s = Search(query, provider='gogoanime')
        results = s.get_results()

        if not results:
            return await status.edit("❌ Kuch nahi mila! Spelling check karo.")

        await status.edit(f"📥 Extracting Links...\n{get_progress_bar(70, 100)}")
        
        anime = results[0]
        dl = downloader.Downloader(anime.get('url'))
        links = dl.get_links(quality='720p') # Aap quality change kar sakte ho

        if not links:
            return await status.edit("❌ Links block hain ya server down hai.")

        # Save to memory for pagination
        chat_id = message.chat.id
        search_db[chat_id] = {"title": anime.get('title'), "links": links}

        await show_episodes(client, chat_id, status.id, page=1)

    except Exception as e:
        await status.edit(f"⚠️ Error: {str(e)}")

async def show_episodes(client, chat_id, message_id, page):
    data = search_db.get(chat_id)
    links = data["links"]
    title = data["title"]

    items_per_page = 10
    total_pages = math.ceil(len(links) / items_per_page)
    
    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    page_links = links[start_idx:end_idx]

    buttons = []
    # Episode Buttons (2 columns)
    row = []
    for i, link in enumerate(page_links):
        ep_num = start_idx + i + 1
        row.append(InlineKeyboardButton(f"Ep {ep_num}", url=link))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row: buttons.append(row)

    # Navigation Buttons
    nav_btns = []
    if page > 1:
        nav_btns.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"page_{page-1}"))
    if page < total_pages:
        nav_btns.append(InlineKeyboardButton("Next ➡️", callback_data=f"page_{page+1}"))
    
    if nav_btns:
        buttons.append(nav_btns)

    text = f"🎯 **Anime:** `{title}`\n📑 **Page:** {page}/{total_pages}\n\n📥 **Niche buttons se download karein:**"
    
    await client.edit_message_text(chat_id, message_id, text, reply_markup=InlineKeyboardMarkup(buttons))

@app.on_callback_query(filters.regex(r"^page_"))
async def handle_pagination(client, callback_query: CallbackQuery):
    page = int(callback_query.data.split("_")[1])
    await show_episodes(client, callback_query.message.chat.id, callback_query.message.id, page)

app.run()
