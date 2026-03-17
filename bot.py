import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    MessageHandler, filters, ContextTypes
)
from typing import Dict, Any
import html

from config import BOT_TOKEN, MAX_EPISODES_PER_PAGE, RESULTS_PER_PAGE
from scraper import scraper
from database import db
from keyboards import *
from utils import paginate_list, safe_html_text

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Store user search states
user_sessions: Dict[int, Dict[str, Any]] = {}

class AnimeBot:
    def __init__(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup all bot handlers"""
        
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("search", self.search_command))
        self.application.add_handler(CommandHandler("favorites", self.favorites_command))
        self.application.add_handler(CommandHandler("recent", self.recent_command))
        self.application.add_handler(CommandHandler("settings", self.settings_command))
        
        # Callback query handler
        self.application.add_handler(CallbackQueryHandler(self.callback_handler))
        
        # Message handler (for text messages)
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Error handler
        self.application.add_error_handler(self.error_handler)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        
        # Add user to database
        db.add_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name
        )
        
        welcome_text = f"""
🌟 *Welcome to Anime Bot, {safe_html_text(user.first_name)}!* 🌟

I can help you find and download your favorite anime!

🔍 *Features:*
• Search any anime by name
• Get download & stream links
• Track your favorites
• View watch history
• Recent releases
• Batch downloads

⚡ *How to use:*
• Send me any anime name
• Use /search <anime name>
• Or use the buttons below

✨ *Enjoy watching!*
        """
        
        await update.message.reply_text(
            welcome_text,
            parse_mode='Markdown',
            reply_markup=main_menu_keyboard()
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
📚 *Anime Bot Help Guide*

*Commands:*
/start - Start the bot
/help - Show this help
/search <name> - Search anime
/favorites - Your favorites
/recent - Recent episodes
/settings - Bot settings

*How to use:*
1. Send anime name directly
2. Use search command
3. Click on results
4. Choose episode
5. Get links!

*Tips:*
• Use specific names
• Add year for accuracy
• Check recent releases
• Save favorites for quick access

Need more help? Contact @YourUsername
        """
        
        await update.message.reply_text(
            help_text,
            parse_mode='Markdown',
            reply_markup=main_menu_keyboard()
        )
    
    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /search command"""
        if not context.args:
            await update.message.reply_text(
                "❌ Please provide an anime name!\nExample: `/search Naruto`",
                parse_mode='Markdown'
            )
            return
        
        query = ' '.join(context.args)
        await self.perform_search(update, query)
    
    async def favorites_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /favorites command"""
        user_id = update.effective_user.id
        user_data = db.users.get(str(user_id), {})
        favorites = user_data.get('favorites', [])
        
        if not favorites:
            await update.message.reply_text(
                "⭐ You don't have any favorites yet!\n"
                "Search for anime and click the ⭐ button to add.",
                reply_markup=main_menu_keyboard()
            )
            return
        
        # Create keyboard with favorites
        keyboard = []
        for anime in favorites[:10]:
            keyboard.append([
                InlineKeyboardButton(anime, callback_data=f"search_{anime}")
            ])
        
        keyboard.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
        
        await update.message.reply_text(
            "⭐ *Your Favorites:*",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def recent_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /recent command"""
        await update.message.reply_text("🔍 Fetching recent episodes...")
        
        recent = await scraper.get_recent_episodes(10)
        
        if not recent:
            await update.message.reply_text(
                "❌ No recent episodes found.",
                reply_markup=main_menu_keyboard()
            )
            return
        
        message = "🆕 *Recent Episodes:*\n\n"
        for ep in recent:
            message += f"• {ep['anime_title']} - Episode {ep['episode']}\n"
        
        keyboard = [[InlineKeyboardButton("🔄 Refresh", callback_data="recent_refresh")]]
        keyboard.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
        
        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /settings command"""
        user_id = update.effective_user.id
        user_data = db.users.get(str(user_id), {})
        settings = user_data.get('settings', {})
        
        await update.message.reply_text(
            "⚙️ *Bot Settings*",
            parse_mode='Markdown',
            reply_markup=settings_keyboard(settings)
        )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
        query = update.message.text.strip()
        
        if len(query) < 2:
            await update.message.reply_text("❌ Please enter at least 2 characters!")
            return
        
        await self.perform_search(update, query)
    
    async def perform_search(self, update: Update, query: str):
        """Perform anime search"""
        user_id = update.effective_user.id
        
        # Send typing action
        await update.message.chat.send_action(action="typing")
        
        # Send searching message
        searching_msg = await update.message.reply_text(
            f"🔍 Searching for *{safe_html_text(query)}*...",
            parse_mode='Markdown'
        )
        
        # Get user settings
        user_data = db.users.get(str(user_id), {})
        settings = user_data.get('settings', {})
        source = settings.get('source', 'gogoanime')
        
        # Perform search
        results = await scraper.search_anime(query, source)
        
        if not results:
            await searching_msg.edit_text(
                f"❌ No results found for *{safe_html_text(query)}*\n\n"
                "Try:\n• Different spelling\n• Shorter name\n• Japanese name",
                parse_mode='Markdown',
                reply_markup=main_menu_keyboard()
            )
            return
        
        # Store results in session
        user_sessions[user_id] = {
            'query': query,
            'results': results,
            'page': 1
        }
        
        # Paginate results
        paginated_results, has_more = paginate_list(results, 1, RESULTS_PER_PAGE)
        total_pages = (len(results) + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE
        
        # Create response
        response = f"📺 *Found {len(results)} results for:*\n`{query}`\n\n"
        for idx, anime in enumerate(paginated_results, 1):
            response += f"*{idx}.* {anime['title']}"
            if anime.get('year'):
                response += f" ({anime['year']})"
            if anime.get('status'):
                response += f" - {anime['status']}"
            response += "\n"
        
        # Update message
        await searching_msg.edit_text(
            response,
            parse_mode='Markdown',
            reply_markup=anime_results_keyboard(
                paginated_results, 
                page=1, 
                total_pages=total_pages
            )
        )
    
    async def callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all callback queries"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        data = query.data
        
        # Main menu navigation
        if data == "main_menu":
            await query.edit_message_text(
                "🏠 *Main Menu*",
                parse_mode='Markdown',
                reply_markup=main_menu_keyboard()
            )
        
        elif data == "menu_search":
            await query.edit_message_text(
                "🔍 *Send me the anime name:*",
                parse_mode='Markdown'
            )
        
        elif data == "menu_favorites":
            user_data = db.users.get(str(user_id), {})
            favorites = user_data.get('favorites', [])
            
            if not favorites:
                await query.edit_message_text(
                    "⭐ No favorites yet!",
                    reply_markup=main_menu_keyboard()
                )
                return
            
            keyboard = []
            for anime in favorites[:10]:
                keyboard.append([
                    InlineKeyboardButton(anime, callback_data=f"search_{anime}")
                ])
            keyboard.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
            
            await query.edit_message_text(
                "⭐ *Your Favorites:*",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        elif data == "menu_history":
            user_data = db.users.get(str(user_id), {})
            history = user_data.get('history', [])
            
            if not history:
                await query.edit_message_text(
                    "📜 No history yet!",
                    reply_markup=main_menu_keyboard()
                )
                return
            
            message = "📜 *Recent History:*\n\n"
            for item in history[:10]:
                message += f"• {item['anime']}"
                if item.get('episode'):
                    message += f" - Ep {item['episode']}"
                message += "\n"
            
            await query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=main_menu_keyboard()
            )
        
        elif data == "menu_settings":
            user_data = db.users.get(str(user_id), {})
            settings = user_data.get('settings', {})
            
            await query.edit_message_text(
                "⚙️ *Settings*",
                parse_mode='Markdown',
                reply_markup=settings_keyboard(settings)
            )
        
        elif data == "menu_recent":
            await query.edit_message_text("🔍 Fetching recent episodes...")
            
            recent = await scraper.get_recent_episodes(10)
            
            if not recent:
                await query.edit_message_text(
                    "❌ No recent episodes.",
                    reply_markup=main_menu_keyboard()
                )
                return
            
            message = "🆕 *Recent Episodes:*\n\n"
            for ep in recent:
                message += f"• {ep['anime_title']} - Ep {ep['episode']}\n"
            
            keyboard = [
                [InlineKeyboardButton("🔄 Refresh", callback_data="recent_refresh")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
            ]
            
            await query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        elif data == "menu_batch":
            await query.edit_message_text(
                "📥 *Batch Download*\n\n"
                "Send anime name to get all episodes:\n"
                "Example: `Naruto batch`",
                parse_mode='Markdown'
            )
        
        elif data == "menu_help":
            await query.edit_message_text(
                "📚 *Help Guide*\n\n"
                "• Send anime name to search\n"
                "• Click on results to see details\n"
                "• Choose episode for links\n"
                "• Use /favorites to save anime\n"
                "• Check /recent for new episodes",
                parse_mode='Markdown',
                reply_markup=main_menu_keyboard()
            )
        
        elif data == "menu_about":
            await query.edit_message_text(
                "ℹ️ *About Anime Bot*\n\n"
                "Version: 2.0\n"
                "Creator: @YourUsername\n"
                "Libraries: PyAniDL, ani-scrapy\n"
                "Sources: GogoAnime, Zoro\n\n"
                "Enjoy watching! 🎬",
                parse_mode='Markdown',
                reply_markup=main_menu_keyboard()
            )
        
        # Handle search results pagination
        elif data.startswith("page_"):
            page = int(data.split("_")[1])
            session = user_sessions.get(user_id, {})
            results = session.get('results', [])
            
            if not results:
                await query.edit_message_text(
                    "❌ Session expired. Please search again.",
                    reply_markup=main_menu_keyboard()
                )
                return
            
            paginated_results, has_more = paginate_list(results, page, RESULTS_PER_PAGE)
            total_pages = (len(results) + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE
            
            session['page'] = page
            user_sessions[user_id] = session
            
            response = f"📺 *Results (Page {page}/{total_pages}):*\n\n"
            for idx, anime in enumerate(paginated_results, (page-1)*RESULTS_PER_PAGE + 1):
                response += f"*{idx}.* {anime['title']}"
                if anime.get('year'):
                    response += f" ({anime['year']})"
                response += "\n"
            
            await query.edit_message_text(
                response,
                parse_mode='Markdown',
                reply_markup=anime_results_keyboard(
                    paginated_results, 
                    page=page, 
                    total_pages=total_pages
                )
            )
        
        # Handle anime selection
        elif data.startswith("anime_"):
            anime_id = data.replace("anime_", "")
            
            await query.edit_message_text(f"📊 Loading details for {anime_id}...")
            
            # Get user settings
            user_data = db.users.get(str(user_id), {})
            settings = user_data.get('settings', {})
            source = settings.get('source', 'gogoanime')
            
            # Get anime details
            details = await scraper.get_anime_details(anime_id, source)
            
            # Check if favorite
            is_favorite = anime_id in user_data.get('favorites', [])
            
            # Add to history
            db.add_to_history(user_id, details['title'])
            
            # Create message
            message = f"📺 *{details['title']}*\n\n"
            if details.get('description'):
                # Truncate description
                desc = details['description'][:200] + "..." if len(details['description']) > 200 else details['description']
                message += f"_{desc}_\n\n"
            
            if details.get('genre'):
                message += f"🎭 *Genre:* {', '.join(details['genre'][:5])}\n"
            if details.get('year'):
                message += f"📅 *Year:* {details['year']}\n"
            if details.get('status'):
                message += f"📊 *Status:* {details['status']}\n"
            if details.get('total_episodes'):
                message += f"🎬 *Episodes:* {details['total_episodes']}\n"
            if details.get('rating'):
                message += f"⭐ *Rating:* {details['rating']}/10\n"
            
            await query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=anime_detail_keyboard(anime_id, is_favorite)
            )
        
        # Handle episode list
        elif data.startswith("episodes_"):
            parts = data.split("_")
            anime_id = parts[1]
            page = int(parts[2]) if len(parts) > 2 else 1
            
            await query.edit_message_text("📋 Loading episodes...")
            
            # Get anime details
            user_data = db.users.get(str(user_id), {})
            settings = user_data.get('settings', {})
            source = settings.get('source', 'gogoanime')
            
            details = await scraper.get_anime_details(anime_id, source)
            episodes = details.get('episodes', [])
            total = details.get('total_episodes', 0)
            
            if not episodes:
                await query.edit_message_text(
                    "❌ No episodes found!",
                    reply_markup=main_menu_keyboard()
                )
                return
            
            await query.edit_message_text(
                f"📋 *Episodes of {details['title']}*\n"
                f"Total: {total} episodes",
                parse_mode='Markdown',
                reply_markup=episodes_keyboard(
                    anime_id, 
                    episodes, 
                    page, 
                    MAX_EPISODES_PER_PAGE, 
                    total
                )
            )
        
        # Handle episode selection
        elif data.startswith("ep_"):
            parts = data.split("_")
            anime_id = parts[1]
            episode_num = int(parts[2])
            
            await query.edit_message_text(f"🔍 Getting links for Episode {episode_num}...")
            
            # Get user settings
            user_data = db.users.get(str(user_id), {})
            settings = user_data.get('settings', {})
            source = settings.get('source', 'gogoanime')
            
            # Get anime title
            details = await scraper.get_anime_details(anime_id, source)
            
            # Get episode links
            download_links, stream_links = await scraper.get_episode_links(
                anime_id, episode_num, source
            )
            
            # Add to history
            db.add_to_history(user_id, details['title'], episode_num)
            
            if not download_links and not stream_links:
                await query.edit_message_text(
                    f"❌ No links found for Episode {episode_num}!\n\n"
                    "Try another source in settings.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("◀️ Back", callback_data=f"episodes_{anime_id}_1")
                    ]])
                )
                return
            
            # Create message
            message = f"📺 *{details['title']} - Episode {episode_num}*\n\n"
            
            if download_links:
                message += "*📥 Available Downloads:*\n"
                for quality in download_links.keys():
                    message += f"• {quality}\n"
                message += "\n"
            
            if stream_links:
                message += "*📺 Available Streams:*\n"
                for quality in stream_links.keys():
                    message += f"• {quality}\n"
            
            await query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=episode_links_keyboard(
                    anime_id, episode_num, download_links, stream_links
                )
            )
        
        # Handle favorite toggle
        elif data.startswith("favorite_"):
            anime_id = data.replace("favorite_", "")
            
            # Get anime title
            user_data = db.users.get(str(user_id), {})
            settings = user_data.get('settings', {})
            source = settings.get('source', 'gogoanime')
            
            details = await scraper.get_anime_details(anime_id, source)
            
            # Toggle favorite
            is_favorite = db.toggle_favorite(user_id, details['title'])
            
            await query.answer(f"⭐ {'Added to' if is_favorite else 'Removed from'} favorites!")
            
            # Update keyboard
            await query.edit_message_reply_markup(
                reply_markup=anime_detail_keyboard(anime_id, is_favorite)
            )
        
        # Handle settings changes
        elif data.startswith("setting_"):
            setting = data.replace("setting_", "")
            
            user_data = db.users.get(str(user_id), {})
            settings = user_data.get('settings', {})
            
            if setting == "source":
                # Toggle source
                current = settings.get('source', 'gogoanime')
                new_source = 'zoro' if current == 'gogoanime' else 'gogoanime'
                db.update_settings(user_id, source=new_source)
                
                await query.answer(f"📺 Source changed to {new_source}")
            
            elif setting == "quality":
                # Cycle through qualities
                qualities = ['360p', '480p', '720p', '1080p']
                current = settings.get('quality', '720p')
                try:
                    idx = qualities.index(current)
                    new_quality = qualities[(idx + 1) % len(qualities)]
                except:
                    new_quality = '720p'
                
                db.update_settings(user_id, quality=new_quality)
                await query.answer(f"🎯 Quality set to {new_quality}")
            
            elif setting == "language":
                # Toggle language
                current = settings.get('language', 'sub')
                new_lang = 'dub' if current == 'sub' else 'sub'
                db.update_settings(user_id, language=new_lang)
                
                await query.answer(f"🔊 Language set to {new_lang}")
            
            elif setting == "notifications":
                # Toggle notifications
                current = settings.get('notifications', True)
                db.update_settings(user_id, notifications=not current)
                
                await query.answer(f"🔔 Notifications {'ON' if not current else 'OFF'}")
            
            # Refresh settings display
            user_data = db.users.get(str(user_id), {})
            settings = user_data.get('settings', {})
            
            await query.edit_message_reply_markup(
                reply_markup=settings_keyboard(settings)
            )
        
        # Handle batch download
        elif data.startswith("batch_"):
            anime_id = data.replace("batch_", "")
            
            await query.edit_message_text(
                "📥 *Batch Download*\n\n"
                "This feature will give you all episodes at once.\n"
                "Processing may take a few minutes...",
                parse_mode='Markdown'
            )
            
            # Get anime details
            user_data = db.users.get(str(user_id), {})
            settings = user_data.get('settings', {})
            source = settings.get('source', 'gogoanime')
            
            details = await scraper.get_anime_details(anime_id, source)
            episodes = details.get('episodes', [])
            
            if not episodes:
                await query.edit_message_text(
                    "❌ No episodes found!",
                    reply_markup=main_menu_keyboard()
                )
                return
            
            # Create batch download message
            message = f"📥 *Batch Download: {details['title']}*\n\n"
            
            for ep_num in episodes[:20]:  # Limit to 20 episodes to avoid long message
                message += f"Ep {ep_num}: [Link]({await self.get_batch_link(anime_id, ep_num, source)})\n"
            
            if len(episodes) > 20:
                message += f"\n... and {len(episodes) - 20} more episodes"
            
            await query.edit_message_text(
                message,
                parse_mode='Markdown',
                disable_web_page_preview=True,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("◀️ Back", callback_data=f"anime_{anime_id}")
                ]])
            )
        
        # Handle back to search
        elif data == "back_to_search":
            session = user_sessions.get(user_id, {})
            query_text = session.get('query', '')
            
            if query_text:
                await self.perform_search(update, query_text)
            else:
                await query.edit_message_text(
                    "🏠 Main Menu",
                    reply_markup=main_menu_keyboard()
                )
        
        # Handle refresh
        elif data == "recent_refresh":
            await self.recent_command(update, context)
    
    async def get_batch_link(self, anime_id: str, episode_num: int, source: str) -> str:
        """Get download link for batch download"""
        download_links, _ = await scraper.get_episode_links(anime_id, episode_num, source)
        
        # Return first available link
        for link in download_links.values():
            return link
        
        return "#"
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")
        
        try:
            if update and update.effective_message:
                await update.effective_message.reply_text(
                    "❌ An error occurred. Please try again later.",
                    reply_markup=main_menu_keyboard()
                )
        except:
            pass
    
    def run(self):
        """Run the bot"""
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

# Create bot instance
bot = AnimeBot()
