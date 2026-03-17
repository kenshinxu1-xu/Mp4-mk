import os
import logging
import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv
from cachetools import TTLCache
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    CallbackQueryHandler, filters, ContextTypes
)
from telegram.constants import ParseMode

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("No BOT_TOKEN found!")
    exit(1)

# Cache
search_cache = TTLCache(maxsize=100, ttl=3600)
episode_cache = TTLCache(maxsize=200, ttl=7200)
user_data = {}  # Store user preferences
user_sessions = {}  # Store current sessions

# ==================== Anime Scraper Class ====================

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
        """Search anime on GogoAnime"""
        cache_key = f"search_{query}"
        if cache_key in search_cache:
            return search_cache[cache_key]
        
        results = []
        try:
            session = await self.get_session()
            search_url = f"https://gogoanime3.co/search.html?keyword={query.replace(' ', '%20')}"
            
            async with session.get(search_url) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    # Parse HTML (simplified - use BeautifulSoup in production)
                    # Demo data for now
                    results = [
                        {
                            "id": "naruto",
                            "title": "Naruto",
                            "year": "2002",
                            "status": "Completed",
                            "episodes": 220,
                            "image": "https://gogocdn.net/cover/naruto.png",
                            "genres": ["Action", "Adventure", "Comedy"],
                            "rating": "8.3"
                        },
                        {
                            "id": "one-piece",
                            "title": "One Piece",
                            "year": "1999",
                            "status": "Ongoing",
                            "episodes": 1089,
                            "image": "https://gogocdn.net/cover/one-piece.png",
                            "genres": ["Action", "Adventure", "Comedy"],
                            "rating": "8.7"
                        },
                        {
                            "id": "bleach",
                            "title": "Bleach",
                            "year": "2004",
                            "status": "Completed",
                            "episodes": 366,
                            "image": "https://gogocdn.net/cover/bleach.png",
                            "genres": ["Action", "Adventure", "Supernatural"],
                            "rating": "8.1"
                        }
                    ]
        except Exception as e:
            logger.error(f"Search error: {e}")
        
        search_cache[cache_key] = results
        return results
    
    async def get_anime_details(self, anime_id: str) -> Dict:
        """Get detailed anime information"""
        # Demo data - replace with actual scraping
        details = {
            "naruto": {
                "title": "Naruto",
                "description": "Naruto Uzumaki, a mischievous adolescent ninja, struggles as he searches for recognition and dreams of becoming the Hokage, the village's leader and strongest ninja.",
                "genres": ["Action", "Adventure", "Comedy", "Martial Arts", "Shounen", "Super Power"],
                "year": "2002",
                "status": "Completed",
                "episodes": 220,
                "rating": "8.3",
                "studio": "Studio Pierrot",
                "duration": "23 min per episode"
            },
            "one-piece": {
                "title": "One Piece",
                "description": "Follows the adventures of Monkey D. Luffy and his pirate crew in order to find the greatest treasure ever left by the legendary Pirate, Gold Roger.",
                "genres": ["Action", "Adventure", "Comedy", "Drama", "Fantasy", "Shounen"],
                "year": "1999",
                "status": "Ongoing",
                "episodes": 1089,
                "rating": "8.7",
                "studio": "Toei Animation",
                "duration": "24 min per episode"
            }
        }
        return details.get(anime_id, {})
    
    async def get_episode_links(self, anime_id: str, episode: int) -> Dict:
        """Get download and stream links for episode"""
        cache_key = f"{anime_id}_ep{episode}"
        if cache_key in episode_cache:
            return episode_cache[cache_key]
        
        # Demo links - replace with actual scraping
        links = {
            "download": {
                "360p": f"https://example.com/{anime_id}/ep{episode}/360.mp4",
                "480p": f"https://example.com/{anime_id}/ep{episode}/480.mp4",
                "720p": f"https://example.com/{anime_id}/ep{episode}/720.mp4",
                "1080p": f"https://example.com/{anime_id}/ep{episode}/1080.mp4"
            },
            "stream": {
                "StreamSB": f"https://streamsb.com/{anime_id}-episode-{episode}",
                "Gogo server": f"https://gogocdn.net/{anime_id}-episode-{episode}.mp4"
            }
        }
        
        episode_cache[cache_key] = links
        return links
    
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

# Initialize scraper
scraper = AnimeScraper()

# ==================== UI Helper Functions ====================

def create_progress_bar(percent: int) -> str:
    """Create a visual progress bar"""
    filled = percent // 10
    empty = 10 - filled
    return "█" * filled + "░" * empty

def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main menu keyboard"""
    keyboard = [
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
        ],
        [
            InlineKeyboardButton("📊 Stats", callback_data="menu_stats"),
            InlineKeyboardButton("🔄 Refresh", callback_data="menu_refresh")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def settings_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Settings keyboard"""
    settings = user_data.get(user_id, {}).get('settings', {
        'source': 'gogoanime',
        'quality': '720p',
        'language': 'sub',
        'notifications': True,
        'auto_next': False
    })
    
    keyboard = [
        [
            InlineKeyboardButton(
                f"📺 Source: {settings['source']}", 
                callback_data="set_source"
            )
        ],
        [
            InlineKeyboardButton(
                f"🎯 Quality: {settings['quality']}", 
                callback_data="set_quality"
            )
        ],
        [
            InlineKeyboardButton(
                f"🔊 Language: {settings['language']}", 
                callback_data="set_lang"
            )
        ],
        [
            InlineKeyboardButton(
                f"🔔 Notifications: {'ON' if settings['notifications'] else 'OFF'}", 
                callback_data="set_notif"
            )
        ],
        [
            InlineKeyboardButton(
                f"⏭️ Auto Next: {'ON' if settings['auto_next'] else 'OFF'}", 
                callback_data="set_auto"
            )
        ],
        [InlineKeyboardButton("🔰 Reset Settings", callback_data="set_reset")],
        [InlineKeyboardButton("◀️ Back", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== Command Handlers ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    logger.info(f"User {user.id} started bot")
    
    # Initialize user data
    if user.id not in user_data:
        user_data[user.id] = {
            'favorites': [],
            'history': [],
            'settings': {
                'source': 'gogoanime',
                'quality': '720p',
                'language': 'sub',
                'notifications': True,
                'auto_next': False
            },
            'joined': datetime.now().isoformat()
        }
    
    welcome_text = f"""
🌟 **✨ ᴡᴇʟᴄᴏᴍᴇ {user.first_name}! ✨** 🌟

╔══════════════════════╗
║   🎬 **ANIME BOT PRO**   ║
╚══════════════════════╝

🔥 **ʀᴇᴀʟ-ᴛɪᴍᴇ ᴘʀᴏɢʀᴇꜱꜱ • ʟɪɴᴋꜱ • ᴅᴏᴡɴʟᴏᴀᴅ**

📌 **ᴄᴏᴍᴍᴀɴᴅꜱ:**
• /start - ᴍᴀɪɴ ᴍᴇɴᴜ
• /help - ʜᴇʟᴘ & ɢᴜɪᴅᴇ
• /search [ɴᴀᴍᴇ] - ꜱᴇᴀʀᴄʜ ᴀɴɪᴍᴇ
• /stats - ʙᴏᴛ ꜱᴛᴀᴛɪꜱᴛɪᴄꜱ
• /settings - ꜱᴇᴛᴛɪɴɢꜱ
• /favorites - ʏᴏᴜʀ ꜰᴀᴠᴏʀɪᴛᴇꜱ

🎯 **ᴛɪᴘ:** ʙᴀꜱ ᴀɴɪᴍᴇ ɴᴀᴍᴇ ʙʜᴇᴊᴏ - ᴍᴀɪɴ ꜱᴇᴀʀᴄʜ ᴋᴀʀᴜɴɢᴀ!

✨ **ʟᴇᴛ'ꜱ ꜱᴛᴀʀᴛ!** 👇
    """
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=main_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """
📚 **✨ ʜᴇʟᴘ & ɢᴜɪᴅᴇ ✨** 📚

╔══════════════════════╗
║   **ʜᴏᴡ ᴛᴏ ᴜꜱᴇ**   ║
╚══════════════════════╝

🔍 **ꜱᴇᴀʀᴄʜ:**
• ᴀɴɪᴍᴇ ɴᴀᴍᴇ ʙʜᴇᴊᴏ (ᴇɢ: `ɴᴀʀᴜᴛᴏ`)
• /search [ɴᴀᴍᴇ] - ᴀᴅᴠᴀɴᴄᴇᴅ ꜱᴇᴀʀᴄʜ

📥 **ᴅᴏᴡɴʟᴏᴀᴅ:**
• ᴇᴘɪꜱᴏᴅᴇ ᴄʜᴜɴᴏ
• Qᴜᴀʟɪᴛʏ ꜱᴇʟᴇᴄᴛ ᴋᴀʀᴏ
• ʟɪɴᴋ ᴘᴀᴏ

🎮 **ʙᴜᴛᴛᴏɴꜱ:**
• 📺 ᴇᴘɪꜱᴏᴅᴇꜱ ʟɪꜱᴛ
• 📥 ᴅᴏᴡɴʟᴏᴀᴅ ʟɪɴᴋꜱ
• ▶️ ꜱᴛʀᴇᴀᴍ ʟɪɴᴋꜱ
• ⭐ ꜰᴀᴠᴏʀɪᴛᴇꜱ
• 📜 ʜɪꜱᴛᴏʀʏ

⚡ **ᴘʀᴏɢʀᴇꜱꜱ ʙᴀʀ:**
█░░░░░░░░░ 10% - ꜱᴇᴀʀᴄʜɪɴɢ...
██████░░░░ 60% - ᴇxᴛʀᴀᴄᴛɪɴɢ...
██████████ 100% - ᴅᴏɴᴇ!

❓ **ᴘʀᴏʙʟᴇᴍ?**
• ꜱᴘᴇʟʟɪɴɢ ᴄʜᴇᴄᴋ ᴋᴀʀᴏ
• ꜰᴜʟʟ ɴᴀᴍᴇ ᴜꜱᴇ ᴋᴀʀᴏ
• ʏᴇᴀʀ ᴀᴅᴅ ᴋᴀʀᴏ (ᴇɢ: `ɴᴀʀᴜᴛᴏ 2002`)

✨ **ᴇɴᴊᴏʏ ᴡᴀᴛᴄʜɪɴɢ!** 🎬
    """
    
    await update.message.reply_text(
        help_text,
        parse_mode=ParseMode.MARKDOWN
    )

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /search command"""
    if not context.args:
        await update.message.reply_text(
            "❌ **ᴀɴɪᴍᴇ ɴᴀᴍᴇ ʙᴀᴛᴀᴏ!**\n"
            "ᴇxᴀᴍᴘʟᴇ: `/search ɴᴀʀᴜᴛᴏ`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    query = ' '.join(context.args)
    await perform_search(update, query)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command"""
    user = update.effective_user
    user_stats = user_data.get(user.id, {})
    
    stats_text = f"""
📊 **✨ ʙᴏᴛ ꜱᴛᴀᴛɪꜱᴛɪᴄꜱ ✨** 📊

╔══════════════════════╗
║   **ʏᴏᴜʀ ᴅᴀᴛᴀ**   ║
╚══════════════════════╝

👤 **ᴜꜱᴇʀ:** {user.first_name}
🆔 **ɪᴅ:** `{user.id}`
⭐ **ꜰᴀᴠᴏʀɪᴛᴇꜱ:** {len(user_stats.get('favorites', []))}
📜 **ʜɪꜱᴛᴏʀʏ:** {len(user_stats.get('history', []))}
📅 **ᴊᴏɪɴᴇᴅ:** {user_stats.get('joined', 'ɴᴇᴡ ᴜꜱᴇʀ')}

╔══════════════════════╗
║   **ɢʟᴏʙᴀʟ**   ║
╚══════════════════════╝

👥 **ᴛᴏᴛᴀʟ ᴜꜱᴇʀꜱ:** {len(user_data)}
💾 **ᴄᴀᴄʜᴇ:** 
  • ꜱᴇᴀʀᴄʜ: {len(search_cache)}
  • ᴇᴘɪꜱᴏᴅᴇ: {len(episode_cache)}
⚡ **ᴜᴘᴛɪᴍᴇ:** ʀᴜɴɴɪɴɢ ꜱɪɴᴄᴇ ꜱᴛᴀʀᴛ

╔══════════════════════╗
║   **ꜱᴇᴛᴛɪɴɢꜱ**   ║
╚══════════════════════╝

📺 ꜱᴏᴜʀᴄᴇ: {user_stats.get('settings', {}).get('source', 'ɢᴏɢᴏᴀɴɪᴍᴇ')}
🎯 Qᴜᴀʟɪᴛʏ: {user_stats.get('settings', {}).get('quality', '720ᴘ')}
🔊 ʟᴀɴɢᴜᴀɢᴇ: {user_stats.get('settings', {}).get('language', 'ꜱᴜʙ')}
🔔 ɴᴏᴛɪꜰɪᴄᴀᴛɪᴏɴꜱ: {'ᴏɴ' if user_stats.get('settings', {}).get('notifications', True) else 'ᴏꜰꜰ'}

✨ **ᴛʜᴀɴᴋꜱ ꜰᴏʀ ᴜꜱɪɴɢ!** 🎬
    """
    
    await update.message.reply_text(
        stats_text,
        parse_mode=ParseMode.MARKDOWN
    )

async def favorites_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /favorites command"""
    user = update.effective_user
    favorites = user_data.get(user.id, {}).get('favorites', [])
    
    if not favorites:
        await update.message.reply_text(
            "⭐ **ɴᴏ ꜰᴀᴠᴏʀɪᴛᴇꜱ ʏᴇᴛ!**\n\n"
            "ᴀɴɪᴍᴇ ᴘᴇ ⭐ ʙᴜᴛᴛᴏɴ ᴅʙᴀᴋᴀᴏ ᴀᴅᴅ ᴋᴀʀɴᴇ ᴋᴇ ʟɪʏᴇ.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    keyboard = []
    for anime in favorites[:10]:
        keyboard.append([
            InlineKeyboardButton(anime, callback_data=f"anime_{anime.lower().replace(' ', '_')}")
        ])
    keyboard.append([InlineKeyboardButton("◀️ Back", callback_data="main_menu")])
    
    await update.message.reply_text(
        "⭐ **ʏᴏᴜʀ ꜰᴀᴠᴏʀɪᴛᴇꜱ:**",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /settings command"""
    user = update.effective_user
    
    await update.message.reply_text(
        "⚙️ **ᴜꜱᴇʀ ꜱᴇᴛᴛɪɴɢꜱ**\n\n"
        "ᴀᴘɴɪ ᴘʀᴇꜰᴇʀᴇɴᴄᴇꜱ ꜱᴇᴛ ᴋᴀʀᴏ:",
        reply_markup=settings_keyboard(user.id),
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle normal text messages (anime names)"""
    query = update.message.text.strip()
    user = update.effective_user
    
    if query.startswith('/'):
        return
    
    if len(query) < 2:
        await update.message.reply_text("❌ ᴋᴀᴍ ꜱᴇ ᴋᴀᴍ 2 ᴄʜᴀʀᴀᴄᴛᴇʀꜱ ᴅᴀᴀʟᴏ!")
        return
    
    logger.info(f"Search query from {user.id}: {query}")
    await perform_search(update, query)

async def perform_search(update: Update, query: str):
    """Perform search with progress bar"""
    user = update.effective_user
    
    # Initial progress message
    status_msg = await update.message.reply_text(
        f"🔍 **ꜱᴇᴀʀᴄʜɪɴɢ:** `{query}`\n\n"
        f"⚡ **ᴘʀᴏɢʀᴇꜱꜱ:**\n"
        f"`{create_progress_bar(0)}` 0%\n"
        f"🔄 ꜱᴛᴀᴛᴜꜱ: ꜱᴛᴀʀᴛɪɴɢ...",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Simulate progress updates
    statuses = ["ꜱᴇᴀʀᴄʜɪɴɢ...", "ꜰᴇᴛᴄʜɪɴɢ ʀᴇꜱᴜʟᴛꜱ...", "ᴘʀᴏᴄᴇꜱꜱɪɴɢ...", "ᴀʟᴍᴏꜱᴛ ᴛʜᴇʀᴇ..."]
    
    for i in range(1, 11):
        await asyncio.sleep(0.3)
        percent = i * 10
        status = statuses[min(i//3, 3)]
        try:
            await status_msg.edit_text(
                f"🔍 **ꜱᴇᴀʀᴄʜɪɴɢ:** `{query}`\n\n"
                f"⚡ **ᴘʀᴏɢʀᴇꜱꜱ:**\n"
                f"`{create_progress_bar(percent)}` {percent}%\n"
                f"🔄 ꜱᴛᴀᴛᴜꜱ: {status}",
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            pass
    
    # Perform actual search
    results = await scraper.search_anime(query)
    
    if not results:
        await status_msg.edit_text(
            f"❌ **ɴᴏ ʀᴇꜱᴜʟᴛꜱ ꜰᴏʀ** `{query}`\n\n"
            f"💡 **ᴛɪᴘꜱ:**\n"
            f"• ꜱᴘᴇʟʟɪɴɢ ᴄʜᴇᴄᴋ ᴋᴀʀᴏ\n"
            f"• ꜰᴜʟʟ ɴᴀᴍᴇ ᴜꜱᴇ ᴋᴀʀᴏ\n"
            f"• ʏᴇᴀʀ ᴀᴅᴅ ᴋᴀʀᴏ (ᴇɢ: `ɴᴀʀᴜᴛᴏ 2002`)",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Add to history
    if user.id in user_data:
        if 'history' not in user_data[user.id]:
            user_data[user.id]['history'] = []
        user_data[user.id]['history'].insert(0, {
            'query': query,
            'time': datetime.now().isoformat()
        })
        user_data[user.id]['history'] = user_data[user.id]['history'][:20]  # Keep last 20
    
    # Display results
    text = f"📺 **ꜰᴏᴜɴᴅ {len(results)} ʀᴇꜱᴜʟᴛꜱ:**\n\n"
    keyboard = []
    
    for idx, anime in enumerate(results[:8], 1):
        text += f"**{idx}.** {anime['title']} ({anime['year']})\n"
        text += f"   ├ ʀᴀᴛɪɴɢ: ⭐ {anime.get('rating', 'N/A')}\n"
        text += f"   └ ꜱᴛᴀᴛᴜꜱ: {anime['status']}\n\n"
        
        keyboard.append([
            InlineKeyboardButton(
                f"{idx}. {anime['title'][:25]}", 
                callback_data=f"anime_{anime['id']}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("🔄 Search Again", callback_data="menu_search"),
        InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
    ])
    
    await status_msg.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all button callbacks"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    data = query.data
    
    logger.info(f"Callback {data} from user {user.id}")
    
    # Main menu
    if data == "main_menu":
        await query.edit_message_text(
            "🏠 **ᴍᴀɪɴ ᴍᴇɴᴜ**\n\nᴋʏᴀ ᴋᴀʀɴᴀ ᴄʜᴀʜᴇɴɢᴇ?",
            reply_markup=main_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    # Search menu
    elif data == "menu_search":
        await query.edit_message_text(
            "🔍 **ᴀɴɪᴍᴇ ɴᴀᴍᴇ ʙʜᴇᴊᴏ:**\n\n"
            "ᴇxᴀᴍᴘʟᴇ: `ɴᴀʀᴜᴛᴏ`, `ᴏɴᴇ ᴘɪᴇᴄᴇ`, `ᴊᴜᴊᴜᴛꜱᴜ ᴋᴀɪꜱᴇɴ`",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Back", callback_data="main_menu")
            ]]),
            parse_mode=ParseMode.MARKDOWN
        )
    
    # Settings menu
    elif data == "menu_settings":
        await query.edit_message_text(
            "⚙️ **ᴜꜱᴇʀ ꜱᴇᴛᴛɪɴɢꜱ**",
            reply_markup=settings_keyboard(user.id),
            parse_mode=ParseMode.MARKDOWN
        )
    
    # Settings toggles
    elif data.startswith("set_"):
        setting = data.replace("set_", "")
        if user.id not in user_data:
            user_data[user.id] = {'settings': {}}
        if 'settings' not in user_data[user.id]:
            user_data[user.id]['settings'] = {}
        
        settings = user_data[user.id]['settings']
        
        if setting == "source":
            sources = ['gogoanime', 'zoro', 'animepahe']
            current = settings.get('source', 'gogoanime')
            idx = sources.index(current) if current in sources else 0
            settings['source'] = sources[(idx + 1) % len(sources)]
            await query.answer(f"📺 ꜱᴏᴜʀᴄᴇ: {settings['source']}")
        
        elif setting == "quality":
            qualities = ['360p', '480p', '720p', '1080p']
            current = settings.get('quality', '720p')
            idx = qualities.index(current) if current in qualities else 2
            settings['quality'] = qualities[(idx + 1) % len(qualities)]
            await query.answer(f"🎯 Qᴜᴀʟɪᴛʏ: {settings['quality']}")
        
        elif setting == "lang":
            langs = ['sub', 'dub']
            current = settings.get('language', 'sub')
            idx = langs.index(current) if current in langs else 0
            settings['language'] = langs[(idx + 1) % len(langs)]
            await query.answer(f"🔊 ʟᴀɴɢᴜᴀɢᴇ: {settings['language']}")
        
        elif setting == "notif":
            settings['notifications'] = not settings.get('notifications', True)
            await query.answer(f"🔔 ɴᴏᴛɪꜰɪᴄᴀᴛɪᴏɴꜱ: {'ᴏɴ' if settings['notifications'] else 'ᴏꜰꜰ'}")
        
        elif setting == "auto":
            settings['auto_next'] = not settings.get('auto_next', False)
            await query.answer(f"⏭️ ᴀᴜᴛᴏ ɴᴇxᴛ: {'ᴏɴ' if settings['auto_next'] else 'ᴏꜰꜰ'}")
        
        elif setting == "reset":
            user_data[user.id]['settings'] = {
                'source': 'gogoanime',
                'quality': '720p',
                'language': 'sub',
                'notifications': True,
                'auto_next': False
            }
            await query.answer("⚙️ ꜱᴇᴛᴛɪɴɢꜱ ʀᴇꜱᴇᴛ!")
        
        # Refresh settings display
        await query.edit_message_reply_markup(
            reply_markup=settings_keyboard(user.id)
        )
    
    # Favorites
    elif data == "menu_fav":
        favorites = user_data.get(user.id, {}).get('favorites', [])
        if not favorites:
            await query.edit_message_text(
                "⭐ **ɴᴏ ꜰᴀᴠᴏʀɪᴛᴇꜱ ʏᴇᴛ!**",
                reply_markup=main_menu_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        keyboard = []
        for anime in favorites[:10]:
            keyboard.append([
                InlineKeyboardButton(anime, callback_data=f"anime_{anime.lower().replace(' ', '_')}")
            ])
        keyboard.append([InlineKeyboardButton("◀️ Back", callback_data="main_menu")])
        
        await query.edit_message_text(
            "⭐ **ʏᴏᴜʀ ꜰᴀᴠᴏʀɪᴛᴇꜱ:**",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    # History
    elif data == "menu_history":
        history = user_data.get(user.id, {}).get('history', [])
        if not history:
            await query.edit_message_text(
                "📜 **ɴᴏ ʜɪꜱᴛᴏʀʏ ʏᴇᴛ!**",
                reply_markup=main_menu_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        text = "📜 **ʀᴇᴄᴇɴᴛ ꜱᴇᴀʀᴄʜᴇꜱ:**\n\n"
        for item in history[:10]:
            text += f"• {item['query']}\n"
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Back", callback_data="main_menu")
            ]]),
            parse_mode=ParseMode.MARKDOWN
        )
    
    # Recent releases
    elif data == "menu_recent":
        await query.edit_message_text(
            "🆕 **ʀᴇᴄᴇɴᴛ ᴇᴘɪꜱᴏᴅᴇꜱ**\n\n"
            "ʏᴇʜ ꜰᴇᴀᴛᴜʀᴇ ᴊᴀʟᴅ ʜɪ ᴀᴀ ʀᴀʜᴀ ʜᴀɪ!",
            reply_markup=main_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    # Batch download
    elif data == "menu_batch":
        await query.edit_message_text(
            "📥 **ʙᴀᴛᴄʜ ᴅᴏᴡɴʟᴏᴀᴅ**\n\n"
            "ᴀɴɪᴍᴇ ɴᴀᴍᴇ ᴋᴇ ꜱᴀᴀᴛʜ `ʙᴀᴛᴄʜ` ʟɪᴋʜᴏ\n"
            "ᴇɢ: `ɴᴀʀᴜᴛᴏ ʙᴀᴛᴄʜ`",
            reply_markup=main_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    # Help
    elif data == "menu_help":
        await help_command(update, context)
    
    # About
    elif data == "menu_about":
        about_text = """
ℹ️ **✨ ᴀʙᴏᴜᴛ ʙᴏᴛ ✨** ℹ️

╔══════════════════════╗
║   **ᴠᴇʀꜱɪᴏɴ 3.0**   ║
╚══════════════════════╝

🎯 **ꜰᴇᴀᴛᴜʀᴇꜱ:**
• ʀᴇᴀʟ-ᴛɪᴍᴇ ᴘʀᴏɢʀᴇꜱꜱ ʙᴀʀ
• ᴍᴜʟᴛɪ-ǫᴜᴀʟɪᴛʏ ᴅᴏᴡɴʟᴏᴀᴅ
• ꜱᴛʀᴇᴀᴍ ʟɪɴᴋꜱ
• ꜰᴀᴠᴏʀɪᴛᴇꜱ/ʜɪꜱᴛᴏʀʏ
• ʙᴀᴛᴄʜ ᴅᴏᴡɴʟᴏᴀᴅ
• ᴄᴜꜱᴛᴏᴍ ꜱᴇᴛᴛɪɴɢꜱ

🛠️ **ᴛᴇᴄʜ:**
• ꜰʀᴀᴍᴇᴡᴏʀᴋ: ᴘʏᴛʜᴏɴ-ᴛᴇʟᴇɢʀᴀᴍ-ʙᴏᴛ
• ʜᴏꜱᴛɪɴɢ: ʀᴀɪʟᴡᴀʏ
• ꜱᴏᴜʀᴄᴇꜱ: ɢᴏɢᴏᴀɴɪᴍᴇ, ᴢᴏʀᴏ

👨‍💻 **ᴅᴇᴠᴇʟᴏᴘᴇʀ:** @ʏᴏᴜʀᴜꜱᴇʀɴᴀᴍᴇ

✨ **ᴇɴᴊᴏʏ!** 🎬
        """
        await query.edit_message_text(
            about_text,
            reply_markup=main_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    # Stats
    elif data == "menu_stats":
        await stats_command(update, context)
    
    # Refresh
    elif data == "menu_refresh":
        await query.edit_message_text(
            "🔄 **ʀᴇꜰʀᴇꜱʜɪɴɢ...**",
            reply_markup=main_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    # Anime details
    elif data.startswith("anime_"):
        anime_id = data.replace("anime_", "")
        
        # Progress
        await query.edit_message_text(
            f"📊 **ʟᴏᴀᴅɪɴɢ ᴀɴɪᴍᴇ ᴅᴇᴛᴀɪʟꜱ...**\n\n"
            f"`{create_progress_bar(0)}` 0%",
            parse_mode=ParseMode.MARKDOWN
        )
        
        for i in range(1, 6):
            await asyncio.sleep(0.2)
            try:
                await query.edit_message_text(
                    f"📊 **ʟᴏᴀᴅɪɴɢ ᴀɴɪᴍᴇ ᴅᴇᴛᴀɪʟꜱ...**\n\n"
                    f"`{create_progress_bar(i*20)}` {i*20}%",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
        
        # Get anime details
        details = await scraper.get_anime_details(anime_id)
        
        if not details:
            await query.edit_message_text(
                "❌ **ᴀɴɪᴍᴇ ɴᴏᴛ ꜰᴏᴜɴᴅ!**",
                reply_markup=main_menu_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Check if favorite
        is_fav = anime_id in user_data.get(user.id, {}).get('favorites', [])
        
        # Create detail text
        detail_text = f"""
📺 **{details.get('title', 'Unknown')}**

📝 **ᴅᴇꜱᴄʀɪᴘᴛɪᴏɴ:**
{details.get('description', 'No description available.')[:200]}...

🎭 **ɢᴇɴʀᴇ:** {', '.join(details.get('genres', ['Unknown'])[:5])}
📅 **ʏᴇᴀʀ:** {details.get('year', 'Unknown')}
📊 **ꜱᴛᴀᴛᴜꜱ:** {details.get('status', 'Unknown')}
🎬 **ᴇᴘɪꜱᴏᴅᴇꜱ:** {details.get('episodes', 'Unknown')}
⭐ **ʀᴀᴛɪɴɢ:** {details.get('rating', 'N/A')}/10
🎬 **ꜱᴛᴜᴅɪᴏ:** {details.get('studio', 'Unknown')}
⏱️ **ᴅᴜʀᴀᴛɪᴏɴ:** {details.get('duration', 'Unknown')}
        """
        
        keyboard = [
            [
                InlineKeyboardButton("📺 ᴇᴘɪꜱᴏᴅᴇꜱ", callback_data=f"eps_{anime_id}_1"),
                InlineKeyboardButton("📥 ᴅᴏᴡɴʟᴏᴀᴅ", callback_data=f"dload_{anime_id}")
            ],
            [
                InlineKeyboardButton(
                    f"{'⭐ ᴜɴꜰᴀᴠᴏʀɪᴛᴇ' if is_fav else '⭐ ꜰᴀᴠᴏʀɪᴛᴇ'}", 
                    callback_data=f"fav_{anime_id}"
                ),
                InlineKeyboardButton("🔍 ꜱɪᴍɪʟᴀʀ", callback_data=f"sim_{anime_id}")
            ],
            [
                InlineKeyboardButton("📥 ʙᴀᴛᴄʜ", callback_data=f"batch_{anime_id}"),
                InlineKeyboardButton("ℹ️ ᴍᴏʀᴇ", callback_data=f"more_{anime_id}")
            ],
            [InlineKeyboardButton("◀️ ʙᴀᴄᴋ ᴛᴏ ꜱᴇᴀʀᴄʜ", callback_data="back_to_search")],
            [InlineKeyboardButton("🏠 ᴍᴀɪɴ ᴍᴇɴᴜ", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(
            detail_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    # Episodes list
    elif data.startswith("eps_"):
        parts = data.split("_")
        anime_id = parts[1]
        page = int(parts[2])
        
        # Progress
        await query.edit_message_text(
            f"📋 **ʟᴏᴀᴅɪɴɢ ᴇᴘɪꜱᴏᴅᴇꜱ...**\n\n"
            f"`{create_progress_bar(0)}` 0%",
            parse_mode=ParseMode.MARKDOWN
        )
        
        for i in range(1, 6):
            await asyncio.sleep(0.15)
            try:
                await query.edit_message_text(
                    f"📋 **ʟᴏᴀᴅɪɴɢ ᴇᴘɪꜱᴏᴅᴇꜱ...**\n\n"
                    f"`{create_progress_bar(i*20)}` {i*20}%",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
        
        # Create episode buttons
        total_episodes = 220  # Demo - get from details
        per_page = 20
        start_ep = (page - 1) * per_page + 1
        end_ep = min(start_ep + per_page - 1, total_episodes)
        
        keyboard = []
        row = []
        
        for ep in range(start_ep, end_ep + 1):
            row.append(InlineKeyboardButton(f"ᴇᴘ {ep}", callback_data=f"ep_{anime_id}_{ep}"))
            if len(row) == 5:
                keyboard.append(row)
                row = []
        
        if row:
            keyboard.append(row)
        
        # Navigation
        nav = []
        total_pages = (total_episodes + per_page - 1) // per_page
        
        if page > 1:
            nav.append(InlineKeyboardButton("◀️ ᴘʀᴇᴠ", callback_data=f"eps_{anime_id}_{page-1}"))
        
        nav.append(InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="noop"))
        
        if page < total_pages:
            nav.append(InlineKeyboardButton("ɴᴇxᴛ ▶️", callback_data=f"eps_{anime_id}_{page+1}"))
        
        keyboard.append(nav)
        keyboard.append([
            InlineKeyboardButton("📥 ʙᴀᴛᴄʜ ᴀʟʟ", callback_data=f"batch_{anime_id}"),
            InlineKeyboardButton("◀️ ʙᴀᴄᴋ", callback_data=f"anime_{anime_id}")
        ])
        
        await query.edit_message_text(
            f"📋 **ᴇᴘɪꜱᴏᴅᴇꜱ {start_ep}-{end_ep} ᴏꜰ {total_episodes}**",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    # Episode links
    elif data.startswith("ep_"):
        parts = data.split("_")
        anime_id = parts[1]
        episode = parts[2]
        
        # Get user settings for quality preference
        settings = user_data.get(user.id, {}).get('settings', {})
        preferred_quality = settings.get('quality', '720p')
        
        # Progress with status updates
        statuses = [
            "ꜰᴇᴛᴄʜɪɴɢ ᴅᴏᴡɴʟᴏᴀᴅ ʟɪɴᴋꜱ...",
            "ꜰɪɴᴅɪɴɢ ꜱᴛʀᴇᴀᴍɪɴɢ ꜱᴏᴜʀᴄᴇꜱ...",
            "ᴇxᴛʀᴀᴄᴛɪɴɢ ʟɪɴᴋꜱ...",
            "ᴘʀᴇᴘᴀʀɪɴɢ ᴅᴏᴡɴʟᴏᴀᴅ...",
            "ᴀʟᴍᴏꜱᴛ ᴛʜᴇʀᴇ..."
        ]
        
        for i in range(1, 11):
            await asyncio.sleep(0.2)
            percent = i * 10
            status = statuses[min(i//2, 4)]
            try:
                await query.edit_message_text(
                    f"🔍 **ɢᴇᴛᴛɪɴɢ ʟɪɴᴋꜱ ꜰᴏʀ ᴇᴘɪꜱᴏᴅᴇ {episode}...**\n\n"
                    f"⚡ **ᴘʀᴏɢʀᴇꜱꜱ:**\n"
                    f"`{create_progress_bar(percent)}` {percent}%\n"
                    f"🔄 **ꜱᴛᴀᴛᴜꜱ:** {status}",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
        
        # Get links
        links = await scraper.get_episode_links(anime_id, int(episode))
        
        # Create keyboard with links
        keyboard = []
        
        # Download links - highlight preferred quality
        if links["download"]:
            keyboard.append([InlineKeyboardButton("📥 **ᴅᴏᴡɴʟᴏᴀᴅ ʟɪɴᴋꜱ**", callback_data="noop")])
            for quality, url in links["download"].items():
                if quality == preferred_quality:
                    btn_text = f"⬇️ {quality} ✨ (ᴘʀᴇꜰᴇʀʀᴇᴅ)"
                else:
                    btn_text = f"⬇️ {quality}"
                keyboard.append([InlineKeyboardButton(btn_text, url=url)])
        
        # Stream links
        if links["stream"]:
            keyboard.append([InlineKeyboardButton("📺 **ꜱᴛʀᴇᴀᴍ ʟɪɴᴋꜱ**", callback_data="noop")])
            for server, url in links["stream"].items():
                keyboard.append([InlineKeyboardButton(f"▶️ {server}", url=url)])
        
        # Navigation
        keyboard.append([
            InlineKeyboardButton("◀️ ᴘʀᴇᴠ ᴇᴘ", callback_data=f"ep_{anime_id}_{int(episode)-1}"),
            InlineKeyboardButton("ɴᴇxᴛ ᴇᴘ ▶️", callback_data=f"ep_{anime_id}_{int(episode)+1}")
        ])
        keyboard.append([
            InlineKeyboardButton("📋 ᴇᴘɪꜱᴏᴅᴇꜱ", callback_data=f"eps_{anime_id}_1"),
            InlineKeyboardButton("◀️ ʙᴀᴄᴋ", callback_data=f"anime_{anime_id}")
        ])
        
        await query.edit_message_text(
            f"📺 **ᴇᴘɪꜱᴏᴅᴇ {episode} ʟɪɴᴋꜱ**\n\n"
            f"✨ ᴘʀᴇꜰᴇʀʀᴇᴅ ǫᴜᴀʟɪᴛʏ: {preferred_quality}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
    
    # Favorite toggle
    elif data.startswith("fav_"):
        anime_id = data.replace("fav_", "")
        
        if user.id not in user_data:
            user_data[user.id] = {'favorites': []}
        if 'favorites' not in user_data[user.id]:
            user_data[user.id]['favorites'] = []
        
        # Get anime title from cache or details
        details = await scraper.get_anime_details(anime_id)
        title = details.get('title', anime_id)
        
        if title in user_data[user.id]['favorites']:
            user_data[user.id]['favorites'].remove(title)
            await query.answer("⭐ ʀᴇᴍᴏᴠᴇᴅ ꜰʀᴏᴍ ꜰᴀᴠᴏʀɪᴛᴇꜱ!")
            is_fav = False
        else:
            user_data[user.id]['favorites'].append(title)
            await query.answer("⭐ ᴀᴅᴅᴇᴅ ᴛᴏ ꜰᴀᴠᴏʀɪᴛᴇꜱ!")
            is_fav = True
        
        # Update keyboard
        keyboard = [
            [
                InlineKeyboardButton("📺 ᴇᴘɪꜱᴏᴅᴇꜱ", callback_data=f"eps_{anime_id}_1"),
                InlineKeyboardButton("📥 ᴅᴏᴡɴʟᴏᴀᴅ", callback_data=f"dload_{anime_id}")
            ],
            [
                InlineKeyboardButton(
                    f"{'⭐ ᴜɴꜰᴀᴠᴏʀɪᴛᴇ' if is_fav else '⭐ ꜰᴀᴠᴏʀɪᴛᴇ'}", 
                    callback_data=f"fav_{anime_id}"
                ),
                InlineKeyboardButton("🔍 ꜱɪᴍɪʟᴀʀ", callback_data=f"sim_{anime_id}")
            ],
            [InlineKeyboardButton("◀️ ʙᴀᴄᴋ", callback_data="main_menu")]
        ]
        
        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # Batch download
    elif data.startswith("batch_"):
        anime_id = data.replace("batch_", "")
        
        await query.edit_message_text(
            f"📥 **ᴘʀᴇᴘᴀʀɪɴɢ ʙᴀᴛᴄʜ ᴅᴏᴡɴʟᴏᴀᴅ...**\n\n"
            f"`{create_progress_bar(0)}` 0%",
            parse_mode=ParseMode.MARKDOWN
        )
        
        for i in range(1, 11):
            await asyncio.sleep(0.3)
            try:
                await query.edit_message_text(
                    f"📥 **ᴘʀᴇᴘᴀʀɪɴɢ ʙᴀᴛᴄʜ ᴅᴏᴡɴʟᴏᴀᴅ...**\n\n"
                    f"`{create_progress_bar(i*10)}` {i*10}%",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
        
        await query.edit_message_text(
            "📥 **ʙᴀᴛᴄʜ ᴅᴏᴡɴʟᴏᴀᴅ**\n\n"
            "ʏᴇʜ ꜰᴇᴀᴛᴜʀᴇ ᴀʙʜɪ ᴅᴇᴠᴇʟᴏᴘᴍᴇɴᴛ ᴍᴇɪɴ ʜᴀɪ.\n"
            "ᴊᴀʟᴅ ʜɪ ᴀᴠᴀɪʟᴀʙʟᴇ ʜᴏɢᴀ!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ ʙᴀᴄᴋ", callback_data=f"anime_{anime_id}")
            ]]),
            parse_mode=ParseMode.MARKDOWN
        )
    
    # No operation
    elif data == "noop":
        pass

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")
    
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ **ᴇʀʀᴏʀ ᴀᴀ ɢʏᴀ!**\nᴋʀᴘʏᴀ ᴅᴏʙᴀʀᴀ ᴋᴏꜱʜɪꜱʜ ᴋᴀʀᴇɪɴ.",
                parse_mode=ParseMode.MARKDOWN
            )
    except:
        pass

# ==================== Main ====================

def main():
    """Start the bot"""
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("favorites", favorites_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_error_handler(error_handler)
    
    # Start bot
    logger.info("Bot starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
