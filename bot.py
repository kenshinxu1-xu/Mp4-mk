import os
import asyncio
import logging
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.enums import ParseMode

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

if not all([API_ID, API_HASH, BOT_TOKEN]):
    logger.error("Missing environment variables!")
    exit(1)

# Initialize Client
app = Client(
    "anime_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ==================== Start Message ====================
START_TEXT = """
🌟 **Ram Ram {name}!** 🌟

Main **Anime Bot** hoon!

🔍 **Bas anime name bhejo:**
`Naruto`, `One Piece`, `Jujutsu Kaisen`

📌 **Commands:**
/start - Start
/help - Help
/search - Search
"""

HELP_TEXT = """
📚 **Help**

• Anime name bhejo - Search karega
• /search [name] - Search
• Buttons use karo navigate karne ke liye

Example: `Naruto` ya `/search Naruto`
"""

# ==================== Handlers ====================

@app.on_message(filters.command("start"))
async def start_cmd(client: Client, message: Message):
    logger.info(f"Start command from {message.from_user.id}")
    await message.reply_text(
        START_TEXT.format(name=message.from_user.first_name),
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔍 Search", callback_data="search"),
            InlineKeyboardButton("❓ Help", callback_data="help")
        ]]),
        parse_mode=ParseMode.MARKDOWN
    )

@app.on_message(filters.command("help"))
async def help_cmd(client: Client, message: Message):
    logger.info(f"Help command from {message.from_user.id}")
    await message.reply_text(HELP_TEXT, parse_mode=ParseMode.MARKDOWN)

@app.on_message(filters.command("search"))
async def search_cmd(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("❌ Anime name batao!\nExample: `/search Naruto`")
        return
    
    query = " ".join(message.command[1:])
    logger.info(f"Search command: {query}")
    
    msg = await message.reply_text(f"🔍 Searching for `{query}`...")
    await asyncio.sleep(1)
    await msg.edit_text(f"❌ `{query}` nahi mila!\nTry different spelling.")

@app.on_message(filters.text)
async def text_handler(client: Client, message: Message):
    if message.text.startswith('/'):
        return
    
    query = message.text.strip()
    logger.info(f"Text search: {query}")
    
    if len(query) < 2:
        await message.reply_text("❌ Kam se kam 2 characters daalo!")
        return
    
    msg = await message.reply_text(f"🔍 Searching for `{query}`...")
    await asyncio.sleep(1)
    await msg.edit_text(
        f"❌ `{query}` nahi mila!\n"
        f"• Spelling check karo\n"
        f"• /search {query} try karo"
    )

# ==================== Callbacks ====================

@app.on_callback_query()
async def callback_handler(client: Client, callback):
    data = callback.data
    await callback.answer()
    
    if data == "search":
        await callback.message.edit_text(
            "🔍 **Anime name bhejo:**",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Back", callback_data="back")
            ]]),
            parse_mode=ParseMode.MARKDOWN
        )
    elif data == "help":
        await callback.message.edit_text(
            HELP_TEXT,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Back", callback_data="back")
            ]]),
            parse_mode=ParseMode.MARKDOWN
        )
    elif data == "back":
        await callback.message.edit_text(
            START_TEXT.format(name=callback.from_user.first_name),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔍 Search", callback_data="search"),
                InlineKeyboardButton("❓ Help", callback_data="help")
            ]]),
            parse_mode=ParseMode.MARKDOWN
        )

# ==================== Main ====================

async def main():
    logger.info("Starting bot...")
    try:
        await app.start()
        logger.info("Bot started! Press Ctrl+C to stop.")
        await asyncio.Event().wait()  # Run forever
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
