import os
import logging
import asyncio
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot token
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("No BOT_TOKEN found!")
    exit(1)

# ==================== Message Handlers ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when /start is issued."""
    user = update.effective_user
    logger.info(f"Start command from user {user.id}")
    
    # Create inline keyboard
    keyboard = [
        [
            InlineKeyboardButton("🔍 Search", callback_data='search'),
            InlineKeyboardButton("❓ Help", callback_data='help')
        ],
        [
            InlineKeyboardButton("ℹ️ About", callback_data='about')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🌟 **Namaste {user.first_name}!** 🌟\n\n"
        f"Main **Anime Bot** hoon!\n\n"
        f"🔍 **Bas anime name bhejo** - turant search karunga!\n"
        f"Example: `Naruto`, `One Piece`, `Jujutsu Kaisen`",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when /help is issued."""
    logger.info(f"Help command from user {update.effective_user.id}")
    await update.message.reply_text(
        "📚 **Help Menu**\n\n"
        "• /start - Start bot\n"
        "• /help - Ye help message\n"
        "• /search [name] - Search anime\n\n"
        "Ya simply anime name bhejo!\n"
        "Example: `Naruto`",
        parse_mode='Markdown'
    )

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search anime."""
    if not context.args:
        await update.message.reply_text("❌ Anime name batao!\nExample: `/search Naruto`")
        return
    
    query = ' '.join(context.args)
    logger.info(f"Search command: {query}")
    
    # Send searching message
    msg = await update.message.reply_text(f"🔍 `{query}` search kar raha hoon...")
    
    # Simulate search
    await asyncio.sleep(2)
    
    # Demo response
    keyboard = [
        [InlineKeyboardButton("📺 Naruto (2002)", callback_data='anime_naruto')],
        [InlineKeyboardButton("◀️ Back", callback_data='back_to_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await msg.edit_text(
        f"📺 **{query} ke results:**\n\n"
        f"1. Naruto (2002) - Completed\n"
        f"2. Naruto Shippuden (2007) - Completed",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle normal text messages (anime names)."""
    query = update.message.text.strip()
    user = update.effective_user
    
    logger.info(f"Text message from {user.id}: {query}")
    
    # Ignore commands
    if query.startswith('/'):
        return
    
    if len(query) < 2:
        await update.message.reply_text("❌ Kam se kam 2 characters daalo!")
        return
    
    # Send searching message
    msg = await update.message.reply_text(f"🔍 `{query}` search kar raha hoon...")
    
    # Simulate search
    await asyncio.sleep(2)
    
    # Demo response
    keyboard = [
        [InlineKeyboardButton("📺 Naruto (2002)", callback_data='anime_naruto')],
        [InlineKeyboardButton("📺 One Piece (1999)", callback_data='anime_onepiece')],
        [InlineKeyboardButton("📺 Bleach (2004)", callback_data='anime_bleach')],
        [InlineKeyboardButton("◀️ Main Menu", callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await msg.edit_text(
        f"📺 **{query} ke results:**\n\n"
        f"Yeh demo results hain - actual search jald aa raha hai!",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button presses."""
    query = update.callback_query
    await query.answer()
    
    logger.info(f"Button pressed: {query.data}")
    
    if query.data == 'search':
        await query.edit_message_text(
            "🔍 **Anime name bhejo:**\nExample: `Naruto`",
            parse_mode='Markdown'
        )
    
    elif query.data == 'help':
        keyboard = [[InlineKeyboardButton("◀️ Back", callback_data='main_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "📚 **Help**\n\n"
            "• Anime name bhejo - search karega\n"
            "• /search [name] - search command\n"
            "• Buttons use karo navigate karne ke liye",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    elif query.data == 'about':
        keyboard = [[InlineKeyboardButton("◀️ Back", callback_data='main_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "ℹ️ **About**\n\n"
            "Bot Version: 1.0\n"
            "Framework: python-telegram-bot\n"
            "Hosting: Railway\n\n"
            "✨ Enjoy Watching!",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    elif query.data == 'main_menu' or query.data == 'back_to_main':
        keyboard = [
            [
                InlineKeyboardButton("🔍 Search", callback_data='search'),
                InlineKeyboardButton("❓ Help", callback_data='help')
            ],
            [
                InlineKeyboardButton("ℹ️ About", callback_data='about')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🏠 **Main Menu**\n\n"
            "Kya karna chahenge aap?",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    elif query.data.startswith('anime_'):
        anime = query.data.replace('anime_', '')
        keyboard = [
            [
                InlineKeyboardButton("📺 Episodes", callback_data=f'eps_{anime}_1'),
                InlineKeyboardButton("📥 Download", callback_data=f'download_{anime}')
            ],
            [InlineKeyboardButton("◀️ Back", callback_data='back_to_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"📺 **{anime.title()}**\n\n"
            f"📝 Description: Demo anime info...\n"
            f"🎭 Genre: Action, Adventure\n"
            f"📅 Year: 2002\n"
            f"🎬 Episodes: 220",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    elif query.data.startswith('eps_'):
        parts = query.data.split('_')
        anime = parts[1]
        page = parts[2]
        
        keyboard = [
            [InlineKeyboardButton("Episode 1", callback_data=f'ep_{anime}_1')],
            [InlineKeyboardButton("Episode 2", callback_data=f'ep_{anime}_2')],
            [InlineKeyboardButton("Episode 3", callback_data=f'ep_{anime}_3')],
            [InlineKeyboardButton("◀️ Back", callback_data=f'anime_{anime}')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"📋 **Episodes - Page {page}**\n\n"
            f"Select episode:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    elif query.data.startswith('ep_'):
        parts = query.data.split('_')
        anime = parts[1]
        episode = parts[2]
        
        keyboard = [
            [InlineKeyboardButton("⬇️ Download 720p", url="https://example.com")],
            [InlineKeyboardButton("⬇️ Download 1080p", url="https://example.com")],
            [InlineKeyboardButton("▶️ Stream", url="https://example.com")],
            [InlineKeyboardButton("◀️ Back", callback_data=f'eps_{anime}_1')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"📺 **Episode {episode}**\n\n"
            f"Links ready hain!",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors."""
    logger.error(f"Update {update} caused error {context.error}")

# ==================== Main ====================

def main():
    """Start the bot."""
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_error_handler(error_handler)
    
    # Start bot
    logger.info("Bot starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
