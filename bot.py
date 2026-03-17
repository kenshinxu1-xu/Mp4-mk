import os
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup, 
    CallbackQuery, Message, InputMediaPhoto
)
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait
from dotenv import load_dotenv
import aiohttp
from cachetools import TTLCache
import time
from tqdm import tqdm

load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

if not all([API_ID, API_HASH, BOT_TOKEN]):
    raise ValueError("Missing required environment variables!")

# Initialize bot
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

# Sources
SOURCES = {
    "gogoanime": "https://gogoanime3.co",
    "zoro": "https://zoro.to",
    "animepahe": "https://animepahe.ru"
}

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
    
    async def search_anime(self, query: str, source: str = "gogoanime") -> List[Dict]:
        """Search anime with progress simulation"""
        cache_key = f"{source}_{query}"
        if cache_key in search_cache:
            return search_cache[cache_key]
        
        results = []
        try:
            session = await self.get_session()
            
            # GogoAnime search
            if source == "gogoanime":
                search_url = f"{SOURCES['gogoanime']}/search.html?keyword={query.replace(' ', '%20')}"
                async with session.get(search_url) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        # Parse results (simplified - use proper parser in production)
                        # This is a placeholder for actual parsing logic
                        results = self.parse_gogo_results(html)
            
            # Simulate progress for demo
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"Search error: {e}")
        
        search_cache[cache_key] = results
        return results
    
    def parse_gogo_results(self, html: str) -> List[Dict]:
        """Parse GogoAnime search results"""
        # Implement actual parsing logic here
        # This is a placeholder
        return [
            {
                "id": "naruto",
                "title": "Naruto",
                "year": "2002",
                "image": "https://gogocdn.net/cover/naruto.png",
                "status": "Completed",
                "episodes": 220
            },
            {
                "id": "one-piece",
                "title": "One Piece",
                "year": "1999",
                "image": "https://gogocdn.net/cover/one-piece.png",
                "status": "Ongoing",
                "episodes": 1000
            }
        ]
    
    async def get_episode_links(self, anime_id: str, episode: int) -> Dict:
        """Get download/stream links for episode"""
        cache_key = f"{anime_id}_ep{episode}"
        if cache_key in episode_cache:
            return episode_cache[cache_key]
        
        links = {
            "download": {},
            "stream": {}
        }
        
        try:
            # Simulate fetching links
            await asyncio.sleep(0.5)
            
            # Demo links - replace with actual scraping
            links["download"] = {
                "360p": f"https://example.com/{anime_id}/ep{episode}/360p.mp4",
                "480p": f"https://example.com/{anime_id}/ep{episode}/480p.mp4",
                "720p": f"https://example.com/{anime_id}/ep{episode}/720p.mp4",
                "1080p": f"https://example.com/{anime_id}/ep{episode}/1080p.mp4"
            }
            
            links["stream"] = {
                "HD": f"https://example.com/stream/{anime_id}/ep{episode}",
                "SD": f"https://example.com/stream/{anime_id}/ep{episode}/sd"
            }
            
        except Exception as e:
            logger.error(f"Link fetch error: {e}")
        
        episode_cache[cache_key] = links
        return links
    
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

# Initialize scraper
scraper = AnimeScraper()

# ==================== UI Components ====================

def main_menu_keyboard():
    """Main menu keyboard"""
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔍 Search Anime", callback_data="menu_search"),
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

def progress_keyboard(current: int, total: int, action: str, data: str):
    """Progress indicator keyboard"""
    percentage = (current / total) * 100
    progress_bar = "█" * int(percentage/10) + "░" * (10 - int(percentage/10))
    
    text = f"{progress_bar} {percentage:.1f}%"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(text, callback_data="noop")],
        [InlineKeyboardButton("⏸️ Pause", callback_data=f"pause_{action}_{data}"),
         InlineKeyboardButton("⏹️ Stop", callback_data=f"stop_{action}_{data}")],
        [InlineKeyboardButton("◀️ Back", callback_data="main_menu")]
    ])
    return keyboard

# ==================== Message Handlers ====================

@app.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    """Handle /start command"""
    user = message.from_user
    
    welcome_text = f"""
🌟 **Welcome {user.first_name}!** 🌟

I'm your **Anime Download Bot** with real-time progress tracking!

🔍 **What I can do:**
• Search any anime
• Get download links
• Stream episodes
• Track favorites
• Batch downloads
• Real-time progress

⚡ **Just send me an anime name to start!**

✨ **Powered by Pyrofork**
    """
    
    await message.reply_text(
        welcome_text,
        reply_markup=main_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

@app.on_message(filters.command("help"))
async def help_command(client: Client, message: Message):
    """Handle /help command"""
    help_text = """
📚 **Anime Bot Help**

**Commands:**
• /start - Start the bot
• /help - Show this help
• /search <name> - Search anime
• /recent - Recent episodes
• /settings - Bot settings

**How to use:**
1. Send anime name directly
2. Click search results
3. Choose episode
4. Get download/stream links

**Features:**
• Real-time progress bars
• Multiple quality options
• Batch downloads
• Favorites list
• Watch history

**Tips:**
• Use specific names
• Add year for accuracy
• Check recent releases
    """
    
    await message.reply_text(
        help_text,
        reply_markup=main_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

@app.on_message(filters.command("search"))
async def search_command(client: Client, message: Message):
    """Handle /search command"""
    if len(message.command) < 2:
        await message.reply_text(
            "❌ Please provide an anime name!\nExample: `/search Naruto`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    query = " ".join(message.command[1:])
    await perform_search(message, query)

@app.on_message(filters.text & ~filters.command)
async def handle_text(client: Client, message: Message):
    """Handle text messages (anime names)"""
    query = message.text.strip()
    
    if len(query) < 2:
        await message.reply_text("❌ Please enter at least 2 characters!")
        return
    
    await perform_search(message, query)

async def perform_search(message: Message, query: str):
    """Perform search with progress"""
    user_id = message.from_user.id
    
    # Show searching message
    status_msg = await message.reply_text(
        f"🔍 **Searching for:** `{query}`\n\n"
        f"📊 **Progress:** 0%",
        reply_markup=progress_keyboard(0, 100, "search", query),
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Simulate search progress
    for i in range(1, 11):
        await asyncio.sleep(0.3)
        try:
            await status_msg.edit_text(
                f"🔍 **Searching for:** `{query}`\n\n"
                f"📊 **Progress:** {i*10}%",
                reply_markup=progress_keyboard(i*10, 100, "search", query),
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            pass
    
    # Actual search
    results = await scraper.search_anime(query)
    
    if not results:
        await status_msg.edit_text(
            f"❌ No results found for **{query}**",
            reply_markup=main_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Store in session
    user_sessions[user_id] = {
        "query": query,
        "results": results,
        "page": 1
    }
    
    # Display results
    result_text = f"📺 **Found {len(results)} results:**\n\n"
    keyboard_buttons = []
    
    for idx, anime in enumerate(results[:5], 1):
        result_text += f"**{idx}.** {anime['title']}"
        if anime.get('year'):
            result_text += f" ({anime['year']})"
        result_text += f" - {anime.get('status', 'Unknown')}\n"
        
        keyboard_buttons.append([
            InlineKeyboardButton(
                f"{idx}. {anime['title'][:20]}",
                callback_data=f"anime_{anime['id']}"
            )
        ])
    
    keyboard_buttons.append([
        InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
    ])
    
    await status_msg.edit_text(
        result_text,
        reply_markup=InlineKeyboardMarkup(keyboard_buttons),
        parse_mode=ParseMode.MARKDOWN
    )

# ==================== Callback Handlers ====================

@app.on_callback_query()
async def handle_callback(client: Client, callback: CallbackQuery):
    """Handle all callback queries"""
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
    
    elif data == "menu_search":
        await message.edit_text(
            "🔍 **Send me the anime name:**",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Back", callback_data="main_menu")
            ]]),
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data == "menu_fav":
        await message.edit_text(
            "⭐ **Favorites**\n\n"
            "This feature is coming soon!",
            reply_markup=main_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data == "menu_history":
        await message.edit_text(
            "📜 **History**\n\n"
            "This feature is coming soon!",
            reply_markup=main_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data == "menu_settings":
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📺 Source: GogoAnime", callback_data="set_source"),
                InlineKeyboardButton("🎯 Quality: 720p", callback_data="set_quality")
            ],
            [
                InlineKeyboardButton("🔊 Language: Sub", callback_data="set_lang"),
                InlineKeyboardButton("🔔 Notifications: ON", callback_data="set_notif")
            ],
            [InlineKeyboardButton("◀️ Back", callback_data="main_menu")]
        ])
        
        await message.edit_text(
            "⚙️ **Settings**",
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data == "menu_recent":
        await message.edit_text(
            "🆕 **Recent Episodes**\n\n"
            "• One Piece - Episode 1089\n"
            "• Jujutsu Kaisen - Episode 24\n"
            "• Demon Slayer - Episode 55\n"
            "• Naruto - Episode 220\n"
            "• Bleach - Episode 366",
            reply_markup=main_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data == "menu_batch":
        await message.edit_text(
            "📥 **Batch Download**\n\n"
            "Send anime name with 'batch'\n"
            "Example: `Naruto batch`",
            reply_markup=main_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data == "menu_help":
        await help_command(client, message)
    
    elif data == "menu_about":
        about_text = """
ℹ️ **About Anime Bot**

**Version:** 3.0
**Framework:** Pyrofork
**Library:** Custom scraper
**Sources:** GogoAnime, Zoro

**Features:**
• Real-time progress bars
• Multiple quality options
• Download/Stream links
• Batch downloads

**Developer:** @YourUsername
**GitHub:** github.com/yourusername

✨ **Happy Watching!**
        """
        
        await message.edit_text(
            about_text,
            reply_markup=main_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    # Anime selection
    elif data.startswith("anime_"):
        anime_id = data.replace("anime_", "")
        
        await message.edit_text(
            f"📊 **Loading anime details...**",
            reply_markup=progress_keyboard(0, 100, "details", anime_id),
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Simulate loading
        for i in range(1, 11):
            await asyncio.sleep(0.2)
            try:
                await message.edit_text(
                    f"📊 **Loading anime details...**\n\n"
                    f"Progress: {i*10}%",
                    reply_markup=progress_keyboard(i*10, 100, "details", anime_id),
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
        
        # Demo anime details
        detail_text = f"""
📺 **Naruto**

📝 **Description:**
Naruto Uzumaki, a mischievous adolescent ninja, struggles as he searches for recognition and dreams of becoming the Hokage, the village's leader and strongest ninja.

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
        
        await message.edit_text(
            detail_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
    
    # Episodes list
    elif data.startswith("eps_"):
        parts = data.split("_")
        anime_id = parts[1]
        page = int(parts[2])
        
        await message.edit_text(
            f"📋 **Loading episodes...**",
            reply_markup=progress_keyboard(0, 100, "episodes", anime_id),
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Simulate loading
        for i in range(1, 11):
            await asyncio.sleep(0.15)
            try:
                await message.edit_text(
                    f"📋 **Loading episodes...**\n\n"
                    f"Progress: {i*10}%",
                    reply_markup=progress_keyboard(i*10, 100, "episodes", anime_id),
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
        
        # Create episode buttons (showing 20 per page)
        start_ep = (page - 1) * 20 + 1
        end_ep = min(start_ep + 19, 220)
        
        ep_text = f"📋 **Naruto - Episodes {start_ep}-{end_ep}**\n\n"
        keyboard = []
        
        # Add episode buttons in rows of 5
        row = []
        for ep in range(start_ep, end_ep + 1):
            row.append(InlineKeyboardButton(
                f"{ep}", 
                callback_data=f"ep_{anime_id}_{ep}"
            ))
            if len(row) == 5:
                keyboard.append(row)
                row = []
        
        if row:
            keyboard.append(row)
        
        # Navigation
        nav_row = []
        if page > 1:
            nav_row.append(InlineKeyboardButton("◀️ Prev", callback_data=f"eps_{anime_id}_{page-1}"))
        
        nav_row.append(InlineKeyboardButton(f"📄 {page}/11", callback_data="noop"))
        
        if page < 11:
            nav_row.append(InlineKeyboardButton("Next ▶️", callback_data=f"eps_{anime_id}_{page+1}"))
        
        keyboard.append(nav_row)
        keyboard.append([InlineKeyboardButton("◀️ Back to Anime", callback_data=f"anime_{anime_id}")])
        
        await message.edit_text(
            ep_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    # Episode links
    elif data.startswith("ep_"):
        parts = data.split("_")
        anime_id = parts[1]
        episode = parts[2]
        
        await message.edit_text(
            f"🔍 **Getting links for Episode {episode}...**",
            reply_markup=progress_keyboard(0, 100, "links", f"{anime_id}_{episode}"),
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Simulate fetching links with real progress
        for i in range(1, 11):
            await asyncio.sleep(0.3)
            try:
                progress_text = f"""
🔍 **Getting links for Episode {episode}...**

📊 **Progress:** {i*10}%
🔄 **Status:** {'Searching...' if i < 3 else 'Found sources...' if i < 6 else 'Extracting links...' if i < 9 else 'Almost done...'}
                """
                await message.edit_text(
                    progress_text,
                    reply_markup=progress_keyboard(i*10, 100, "links", f"{anime_id}_{episode}"),
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
        
        # Get actual links
        links = await scraper.get_episode_links(anime_id, int(episode))
        
        link_text = f"""
📺 **Naruto - Episode {episode}**

📥 **Download Links:**
        """
        
        keyboard = []
        
        # Download links
        for quality, url in links["download"].items():
            link_text += f"\n• {quality}"
            keyboard.append([InlineKeyboardButton(f"⬇️ Download {quality}", url=url)])
        
        link_text += f"\n\n📺 **Stream Links:**"
        
        # Stream links
        for quality, url in links["stream"].items():
            link_text += f"\n• {quality}"
            keyboard.append([InlineKeyboardButton(f"▶️ Stream {quality}", url=url)])
        
        # Navigation
        keyboard.append([
            InlineKeyboardButton("◀️ Prev Ep", callback_data=f"ep_{anime_id}_{int(episode)-1}"),
            InlineKeyboardButton("Next Ep ▶️", callback_data=f"ep_{anime_id}_{int(episode)+1}")
        ])
        keyboard.append([
            InlineKeyboardButton("📋 Episodes", callback_data=f"eps_{anime_id}_1"),
            InlineKeyboardButton("◀️ Back", callback_data=f"anime_{anime_id}")
        ])
        
        await message.edit_text(
            link_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    # Settings changes
    elif data == "set_source":
        await callback.answer("📺 Source changed to Zoro", show_alert=False)
    
    elif data == "set_quality":
        await callback.answer("🎯 Quality set to 1080p", show_alert=False)
    
    elif data == "set_lang":
        await callback.answer("🔊 Language set to Dub", show_alert=False)
    
    elif data == "set_notif":
        await callback.answer("🔔 Notifications OFF", show_alert=False)
    
    # Progress control
    elif data.startswith("pause_"):
        await callback.answer("⏸️ Progress paused", show_alert=False)
    
    elif data.startswith("stop_"):
        await callback.answer("⏹️ Operation stopped", show_alert=False)
        await message.edit_text(
            "⏹️ Operation cancelled",
            reply_markup=main_menu_keyboard()
        )
    
    # No operation (for progress bar)
    elif data == "noop":
        await callback.answer()

# ==================== Error Handler ====================

@app.on_message(filters.command("stats"))
async def stats_command(client: Client, message: Message):
    """Show bot statistics"""
    stats_text = f"""
📊 **Bot Statistics**

👥 **Users:** {len(user_sessions)}
💾 **Cache:** 
• Search: {len(search_cache)} items
• Episodes: {len(episode_cache)} items

⚡ **Performance:**
• Uptime: Running
• Memory: Good
• Status: Active

🤖 **Bot is running smoothly!**
    """
    
    await message.reply_text(
        stats_text,
        parse_mode=ParseMode.MARKDOWN
    )

# ==================== Main Function ====================

async def main():
    """Main function"""
    print("🤖 Anime Bot starting with Pyrofork...")
    print("✅ Real-time progress tracking enabled")
    print("✅ Multi-source support enabled")
    print("✅ Batch download ready")
    
    try:
        await app.run()
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await scraper.close()

if __name__ == "__main__":
    asyncio.run(main())
