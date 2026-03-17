import os
import asyncio
import logging
from typing import Dict, List, Optional
from dotenv import load_dotenv
from cachetools import TTLCache
import aiohttp
from pyrofork import Client, filters
from pyrofork.types import (
    Message, InlineKeyboardButton, InlineKeyboardMarkup,
    CallbackQuery
)
from pyrofork.enums import ParseMode
from pyrofork.errors import FloodWait

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

if not all([API_ID, API_HASH, BOT_TOKEN]):
    logger.error("Missing required environment variables!")
    logger.error("Please set API_ID, API_HASH, and BOT_TOKEN in .env file")
    exit(1)

# Initialize Pyrofork Client
app = Client(
    "anime_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Cache
search_cache = TTLCache(maxsize=100, ttl=3600)
episode_cache = TTLCache(maxsize=200, ttl=7200)
user_sessions = {}

# ==================== Scraper Class ====================

class AnimeScraper:
    def __init__(self):
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    async def get_session(self):
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession(headers=self.headers)
        return self.session
    
    async def search_anime(self, query: str) -> List[Dict]:
        """Search anime (simulated for demo)"""
        # In production, implement actual scraping
        # For now, return demo data
        await asyncio.sleep(1)  # Simulate network delay
        return [
            {
                "id": "naruto",
                "title": "Naruto",
                "year": "2002",
                "status": "Completed",
                "episodes": 220,
                "image": "https://via.placeholder.com/150"
            },
            {
                "id": "one-piece",
                "title": "One Piece",
                "year": "1999",
                "status": "Ongoing",
                "episodes": 1000,
                "image": "https://via.placeholder.com/150"
            },
            {
                "id": "bleach",
                "title": "Bleach",
                "year": "2004",
                "status": "Completed",
                "episodes": 366,
                "image": "https://via.placeholder.com/150"
            }
        ]
    
    async def get_episode_links(self, anime_id: str, episode: int) -> Dict:
        """Get download/stream links (simulated)"""
        await asyncio.sleep(0.5)
        return {
            "download": {
                "360p": f"https://example.com/{anime_id}/ep{episode}/360.mp4",
                "480p": f"https://example.com/{anime_id}/ep{episode}/480.mp4",
                "720p": f"https://example.com/{anime_id}/ep{episode}/720.mp4",
                "1080p": f"https://example.com/{anime_id}/ep{episode}/1080.mp4"
            },
            "stream": {
                "HD": f"https://example.com/stream/{anime_id}/{episode}/hd",
                "SD": f"https://example.com/stream/{anime_id}/{episode}/sd"
            }
        }
    
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

scraper = AnimeScraper()

# ==================== Helper Functions ====================

def progress_keyboard(percent: int, action: str, data: str) -> InlineKeyboardMarkup:
    """Create progress bar keyboard"""
    filled = percent // 10
    empty = 10 - filled
    bar = "█" * filled + "░" * empty
    text = f"{bar} {percent}%"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(text, callback_data="noop")],
        [
            InlineKeyboardButton("⏸️ Pause", callback_data=f"pause_{action}_{data}"),
            InlineKeyboardButton("⏹️ Stop", callback_data=f"stop_{action}_{data}")
        ],
        [InlineKeyboardButton("◀️ Back", callback_data="main_menu")]
    ])
    return keyboard

def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main menu keyboard"""
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔍 Search", callback_data="menu_search"),
            InlineKeyboardButton("⭐ Favorites", callback_data="menu_fav")
        ],
        [
            InlineKeyboardButton("📜 History", callback_data="menu_history"),
            InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings")
        ],
        [
            InlineKeyboardButton("🆕 Recent", callback_data="menu_recent"),
            InlineKeyboardButton("📥 Batch", callback_data="menu_batch")
        ],
        [
            InlineKeyboardButton("❓ Help", callback_data="menu_help"),
            InlineKeyboardButton("ℹ️ About", callback_data="menu_about")
        ]
    ])
    return keyboard

# ==================== Command Handlers ====================

@app.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    user = message.from_user
    await message.reply_text(
        f"🌟 **Welcome {user.first_name}!** 🌟\n\n"
        "I'm your Anime Bot with real-time progress!\n\n"
        "🔍 **Send me an anime name to start searching.**",
        reply_markup=main_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

@app.on_message(filters.command("help"))
async def help_command(client: Client, message: Message):
    await message.reply_text(
        "📚 **Help**\n\n"
        "• Send anime name to search\n"
        "• Use /search <name>\n"
        "• Use buttons to navigate\n"
        "• Real-time progress shown",
        reply_markup=main_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

@app.on_message(filters.command("search"))
async def search_command(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("❌ Please provide an anime name!")
        return
    query = " ".join(message.command[1:])
    await perform_search(message, query)

@app.on_message(filters.text & ~filters.command)
async def text_handler(client: Client, message: Message):
    query = message.text.strip()
    if len(query) < 2:
        await message.reply_text("❌ Please enter at least 2 characters!")
        return
    await perform_search(message, query)

async def perform_search(message: Message, query: str):
    """Search with progress animation"""
    user_id = message.from_user.id
    
    # Initial progress message
    status_msg = await message.reply_text(
        f"🔍 **Searching:** `{query}`\n\n"
        f"Progress: 0%",
        reply_markup=progress_keyboard(0, "search", query),
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Simulate progress updates
    for percent in range(10, 101, 10):
        await asyncio.sleep(0.3)
        try:
            await status_msg.edit_text(
                f"🔍 **Searching:** `{query}`\n\n"
                f"Progress: {percent}%",
                reply_markup=progress_keyboard(percent, "search", query),
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            pass
    
    # Perform actual search
    results = await scraper.search_anime(query)
    
    if not results:
        await status_msg.edit_text(
            f"❌ No results for **{query}**",
            reply_markup=main_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Store results in session
    user_sessions[user_id] = {"results": results, "page": 1}
    
    # Display results
    text = f"📺 **Found {len(results)} results:**\n\n"
    keyboard_buttons = []
    
    for idx, anime in enumerate(results[:5], 1):
        text += f"**{idx}.** {anime['title']} ({anime['year']}) - {anime['status']}\n"
        keyboard_buttons.append([
            InlineKeyboardButton(f"{idx}. {anime['title'][:20]}", callback_data=f"anime_{anime['id']}")
        ])
    
    keyboard_buttons.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
    
    await status_msg.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard_buttons),
        parse_mode=ParseMode.MARKDOWN
    )

# ==================== Callback Handlers ====================

@app.on_callback_query()
async def callback_handler(client: Client, callback: CallbackQuery):
    data = callback.data
    user_id = callback.from_user.id
    message = callback.message
    
    await callback.answer()
    
    # Main menu
    if data == "main_menu":
        await message.edit_text(
            "🏠 **Main Menu**",
            reply_markup=main_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    # Search menu
    elif data == "menu_search":
        await message.edit_text(
            "🔍 **Send me the anime name:**",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Back", callback_data="main_menu")
            ]]),
            parse_mode=ParseMode.MARKDOWN
        )
    
    # Placeholder for other menus
    elif data in ["menu_fav", "menu_history", "menu_settings", "menu_recent", "menu_batch", "menu_help", "menu_about"]:
        await message.edit_text(
            f"🛠️ This feature is under development.\n\nYou clicked: {data}",
            reply_markup=main_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    # Anime details
    elif data.startswith("anime_"):
        anime_id = data.replace("anime_", "")
        
        # Progress simulation
        await message.edit_text(
            "📊 **Loading anime details...**\n\nProgress: 0%",
            reply_markup=progress_keyboard(0, "details", anime_id),
            parse_mode=ParseMode.MARKDOWN
        )
        
        for percent in range(10, 101, 10):
            await asyncio.sleep(0.2)
            await message.edit_text(
                f"📊 **Loading anime details...**\n\nProgress: {percent}%",
                reply_markup=progress_keyboard(percent, "details", anime_id),
                parse_mode=ParseMode.MARKDOWN
            )
        
        # Show anime info (demo)
        text = """
📺 **Naruto**

📝 **Description:** Naruto Uzumaki, a mischievous adolescent ninja, struggles as he searches for recognition and dreams of becoming the Hokage.

🎭 **Genre:** Action, Adventure, Comedy
📅 **Year:** 2002
📊 **Status:** Completed
🎬 **Episodes:** 220
⭐ **Rating:** 8.3/10
        """
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📺 Episodes", callback_data=f"eps_{anime_id}_1"),
                InlineKeyboardButton("📥 Download", callback_data=f"download_{anime_id}")
            ],
            [
                InlineKeyboardButton("⭐ Favorite", callback_data=f"fav_{anime_id}"),
                InlineKeyboardButton("🔍 Similar", callback_data=f"similar_{anime_id}")
            ],
            [InlineKeyboardButton("◀️ Back", callback_data="main_menu")]
        ])
        
        await message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    
    # Episodes list
    elif data.startswith("eps_"):
        parts = data.split("_")
        anime_id = parts[1]
        page = int(parts[2])
        
        await message.edit_text(
            f"📋 **Loading episodes...**\n\nProgress: 0%",
            reply_markup=progress_keyboard(0, "episodes", anime_id),
            parse_mode=ParseMode.MARKDOWN
        )
        
        for percent in range(10, 101, 10):
            await asyncio.sleep(0.15)
            await message.edit_text(
                f"📋 **Loading episodes...**\n\nProgress: {percent}%",
                reply_markup=progress_keyboard(percent, "episodes", anime_id),
                parse_mode=ParseMode.MARKDOWN
            )
        
        # Create episode buttons (20 per page)
        start_ep = (page - 1) * 20 + 1
        end_ep = min(start_ep + 19, 220)
        
        keyboard = []
        row = []
        for ep in range(start_ep, end_ep + 1):
            row.append(InlineKeyboardButton(str(ep), callback_data=f"ep_{anime_id}_{ep}"))
            if len(row) == 5:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        
        # Navigation
        nav = []
        if page > 1:
            nav.append(InlineKeyboardButton("◀️ Prev", callback_data=f"eps_{anime_id}_{page-1}"))
        nav.append(InlineKeyboardButton(f"📄 {page}/11", callback_data="noop"))
        if page < 11:
            nav.append(InlineKeyboardButton("Next ▶️", callback_data=f"eps_{anime_id}_{page+1}"))
        keyboard.append(nav)
        keyboard.append([InlineKeyboardButton("◀️ Back", callback_data=f"anime_{anime_id}")])
        
        await message.edit_text(
            f"📋 **Episodes {start_ep}-{end_ep}**",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    # Episode links
    elif data.startswith("ep_"):
        parts = data.split("_")
        anime_id = parts[1]
        episode = parts[2]
        
        await message.edit_text(
            f"🔍 **Getting links for Episode {episode}...**\n\nProgress: 0%",
            reply_markup=progress_keyboard(0, "links", f"{anime_id}_{episode}"),
            parse_mode=ParseMode.MARKDOWN
        )
        
        statuses = ["Searching sources...", "Extracting links...", "Almost done..."]
        for i in range(1, 11):
            await asyncio.sleep(0.25)
            status = statuses[min(i//4, 2)]
            await message.edit_text(
                f"🔍 **Getting links for Episode {episode}...**\n\n"
                f"Progress: {i*10}%\n"
                f"Status: {status}",
                reply_markup=progress_keyboard(i*10, "links", f"{anime_id}_{episode}"),
                parse_mode=ParseMode.MARKDOWN
            )
        
        # Get links (simulated)
        links = await scraper.get_episode_links(anime_id, int(episode))
        
        text = f"📺 **Naruto - Episode {episode}**\n\n"
        keyboard = []
        
        if links["download"]:
            text += "📥 **Download Links:**\n"
            for quality, url in links["download"].items():
                text += f"• {quality}\n"
                keyboard.append([InlineKeyboardButton(f"⬇️ Download {quality}", url=url)])
            text += "\n"
        
        if links["stream"]:
            text += "📺 **Stream Links:**\n"
            for quality, url in links["stream"].items():
                text += f"• {quality}\n"
                keyboard.append([InlineKeyboardButton(f"▶️ Stream {quality}", url=url)])
            text += "\n"
        
        # Navigation
        keyboard.append([
            InlineKeyboardButton("◀️ Prev", callback_data=f"ep_{anime_id}_{int(episode)-1}"),
            InlineKeyboardButton("Next ▶️", callback_data=f"ep_{anime_id}_{int(episode)+1}")
        ])
        keyboard.append([
            InlineKeyboardButton("📋 Episodes", callback_data=f"eps_{anime_id}_1"),
            InlineKeyboardButton("◀️ Back", callback_data=f"anime_{anime_id}")
        ])
        
        await message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
    
    # Progress control
    elif data.startswith("pause_"):
        await callback.answer("⏸️ Paused (demo)")
    elif data.startswith("stop_"):
        await callback.answer("⏹️ Stopped")
        await message.edit_text(
            "⏹️ Operation cancelled.",
            reply_markup=main_menu_keyboard()
        )
    elif data == "noop":
        await callback.answer()

# ==================== Error Handler ====================

@app.on_message(filters.command("stats"))
async def stats_command(client: Client, message: Message):
    await message.reply_text(
        f"📊 **Bot Statistics**\n\n"
        f"👥 Active users: {len(user_sessions)}\n"
        f"💾 Cache: {len(search_cache)} searches, {len(episode_cache)} episodes\n"
        f"⚡ Status: Running smoothly",
        parse_mode=ParseMode.MARKDOWN
    )

# ==================== Main ====================

async def main():
    logger.info("Starting Anime Bot with Pyrofork...")
    try:
        await app.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        await scraper.close()
        logger.info("Cleanup done")

if __name__ == "__main__":
    asyncio.run(main())
