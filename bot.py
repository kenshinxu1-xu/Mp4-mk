import os
import logging
import asyncio
import aiohttp
from urllib.parse import quote
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from cachetools import TTLCache
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    CallbackQueryHandler, filters, ContextTypes
)
from telegram.constants import ParseMode

load_dotenv()
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("No BOT_TOKEN found!")
    exit(1)

# Cache
search_cache = TTLCache(maxsize=50, ttl=1800)  # 30 minutes
episode_cache = TTLCache(maxsize=100, ttl=3600)  # 1 hour

class AnimeScraper:
    def __init__(self):
        self.session = None
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        # Multiple sources - pehle Hindi sites try karega
        self.sources = [
            {
                'name': 'animedubhindi',
                'search_url': 'https://animedubhindi.me/?s={}',
                'base_url': 'https://animedubhindi.me'
            },
            {
                'name': 'animesalt',
                'search_url': 'https://animesalt.in/search?q={}',
                'base_url': 'https://animesalt.in'
            },
            {
                'name': 'gogoanime',
                'search_url': 'https://gogoanime3.co/search.html?keyword={}',
                'base_url': 'https://gogoanime3.co'
            }
        ]
    
    async def get_session(self):
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession(headers=self.headers)
        return self.session
    
    async def search_anime(self, query: str) -> list:
        """Search across all sources"""
        cache_key = f"search_{query}"
        if cache_key in search_cache:
            return search_cache[cache_key]
        
        results = []
        session = await self.get_session()
        
        for source in self.sources:
            try:
                search_url = source['search_url'].format(quote(query))
                async with session.get(search_url, timeout=10) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        if source['name'] == 'gogoanime':
                            items = soup.select('div.img a')[:5]
                            for item in items:
                                title = item.get('title', '')
                                if title:
                                    results.append({
                                        'title': title,
                                        'url': source['base_url'] + item.get('href', ''),
                                        'source': source['name'],
                                        'id': item.get('href', '').split('/')[-1]
                                    })
                        
                        elif source['name'] == 'animedubhindi':
                            items = soup.select('article h2 a')[:5]
                            for item in items:
                                results.append({
                                    'title': item.text.strip(),
                                    'url': item.get('href', ''),
                                    'source': source['name'],
                                    'id': item.get('href', '').split('/')[-2] if item.get('href') else ''
                                })
                        
                        elif source['name'] == 'animesalt':
                            items = soup.select('a.block')[:5]
                            for item in items:
                                title_tag = item.select_one('h3')
                                if title_tag:
                                    results.append({
                                        'title': title_tag.text.strip(),
                                        'url': source['base_url'] + item.get('href', ''),
                                        'source': source['name'],
                                        'id': item.get('href', '').split('/')[-1]
                                    })
            except Exception as e:
                logger.error(f"Error searching {source['name']}: {e}")
                continue
        
        search_cache[cache_key] = results
        return results
    
    async def get_episodes(self, anime_url: str, source: str) -> list:
        """Get episodes list from anime page"""
        cache_key = f"eps_{anime_url}"
        if cache_key in episode_cache:
            return episode_cache[cache_key]
        
        episodes = []
        session = await self.get_session()
        
        try:
            async with session.get(anime_url, timeout=10) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    if source == 'gogoanime':
                        ep_links = soup.select('ul#episode_related li a')
                        for link in ep_links[:50]:  # Max 50 episodes
                            ep_num = link.text.strip().replace('EP', '').strip()
                            if ep_num.isdigit():
                                episodes.append({
                                    'number': int(ep_num),
                                    'url': link.get('href', '')
                                })
                    
                    elif source == 'animedubhindi':
                        ep_links = soup.select('div.eplister a')
                        for link in ep_links[:50]:
                            ep_num = link.select_one('.epl-num')
                            if ep_num:
                                episodes.append({
                                    'number': int(ep_num.text.strip()),
                                    'url': link.get('href', '')
                                })
                    
                    elif source == 'animesalt':
                        ep_links = soup.select('a.episode-link')
                        for link in ep_links[:50]:
                            ep_num = link.select_one('span')
                            if ep_num:
                                episodes.append({
                                    'number': len(episodes) + 1,
                                    'url': link.get('href', '')
                                })
        except Exception as e:
            logger.error(f"Error getting episodes: {e}")
        
        # Sort by episode number
        episodes.sort(key=lambda x: x['number'])
        episode_cache[cache_key] = episodes
        return episodes
    
    async def get_download_links(self, episode_url: str) -> dict:
        """Extract download links from episode page"""
        links = {}
        session = await self.get_session()
        
        try:
            async with session.get(episode_url, timeout=10) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Find download links
                    download_div = soup.find('div', class_='download-links') or soup.find('div', class_='mirror_link')
                    if download_div:
                        for link in download_div.find_all('a'):
                            text = link.text.lower()
                            url = link.get('href', '')
                            if '1080' in text:
                                links['1080p'] = url
                            elif '720' in text:
                                links['720p'] = url
                            elif '480' in text:
                                links['480p'] = url
                            elif '360' in text:
                                links['360p'] = url
                    
                    # If no links found, try direct video links
                    if not links:
                        video = soup.find('video')
                        if video and video.find('source'):
                            links['Direct'] = video.find('source').get('src', '')
        except Exception as e:
            logger.error(f"Error getting download links: {e}")
        
        return links
    
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

scraper = AnimeScraper()

# ==================== BOT HANDLERS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"👋 **Namaste {user.first_name}!**\n\n"
        f"Main **Anime Download Bot** hoon.\n\n"
        f"🔍 **Bas anime name bhejo** - main search karunga!\n"
        f"🎯 Hindi dubbed aur subbed dono milega.\n\n"
        f"Example: `Naruto`, `One Piece`, `Jujutsu Kaisen`",
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    
    if query.startswith('/') or len(query) < 3:
        return
    
    msg = await update.message.reply_text(f"🔍 `{query}` search kar raha hoon...")
    
    results = await scraper.search_anime(query)
    
    if not results:
        await msg.edit_text(
            f"❌ `{query}` nahi mila!\n\n"
            f"💡 Tips:\n"
            f"• Spelling check karo\n"
            f"• Full name use karo\n"
            f"• English name try karo",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    keyboard = []
    for i, anime in enumerate(results[:8], 1):
        keyboard.append([
            InlineKeyboardButton(
                f"{i}. {anime['title'][:35]}",
                callback_data=f"anime_{i}"
            )
        ])
        # Store in context for later
        if 'results' not in context.user_data:
            context.user_data['results'] = {}
        context.user_data['results'][str(i)] = anime
    
    await msg.edit_text(
        f"📺 **{len(results)} results mil gaye:**\n\n"
        f"Neche se choose karo:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_data = context.user_data
    
    if data.startswith('anime_'):
        idx = data.replace('anime_', '')
        anime = user_data.get('results', {}).get(idx)
        
        if not anime:
            await query.edit_message_text("Session expired! Dobara search karo.")
            return
        
        await query.edit_message_text(
            f"📺 **{anime['title']}**\n\n"
            f"📥 Episodes fetch kar raha hoon...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        episodes = await scraper.get_episodes(anime['url'], anime['source'])
        
        if not episodes:
            await query.edit_message_text(
                f"❌ Episodes nahi mile!\n{anime['url']}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("◀️ Back", callback_data="back_search")
                ]])
            )
            return
        
        # Store episodes
        user_data['episodes'] = episodes
        user_data['anime_title'] = anime['title']
        
        # Create episode keyboard
        keyboard = []
        row = []
        for i, ep in enumerate(episodes[:20], 1):
            row.append(InlineKeyboardButton(f"{ep['number']}", callback_data=f"ep_{i-1}"))
            if len(row) == 5:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("◀️ Back", callback_data="back_search")])
        
        await query.edit_message_text(
            f"📺 **{anime['title']}**\n"
            f"Total: {len(episodes)} episodes\n\n"
            f"Episode choose karo:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data.startswith('ep_'):
        idx = int(data.replace('ep_', ''))
        episodes = user_data.get('episodes', [])
        
        if idx >= len(episodes):
            await query.edit_message_text("Error! Dobara try karo.")
            return
        
        ep = episodes[idx]
        
        await query.edit_message_text(
            f"🔍 Download links fetch kar raha hoon...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        links = await scraper.get_download_links(ep['url'])
        
        if not links:
            await query.edit_message_text(
                f"❌ Download links nahi mile!\n{ep['url']}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("◀️ Back", callback_data=f"back_ep")
                ]])
            )
            return
        
        keyboard = []
        for quality, url in links.items():
            keyboard.append([InlineKeyboardButton(f"⬇️ Download {quality}", url=url)])
        
        keyboard.append([
            InlineKeyboardButton("◀️ Back to Episodes", callback_data="back_ep")
        ])
        
        title = user_data.get('anime_title', 'Anime')
        await query.edit_message_text(
            f"📺 **{title} - Episode {ep['number']}**\n\n"
            f"✅ {len(links)} links available:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
    
    elif data == "back_ep":
        # Go back to episodes list
        episodes = user_data.get('episodes', [])
        title = user_data.get('anime_title', 'Anime')
        
        keyboard = []
        row = []
        for i, ep in enumerate(episodes[:20], 1):
            row.append(InlineKeyboardButton(f"{ep['number']}", callback_data=f"ep_{i-1}"))
            if len(row) == 5:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("◀️ Back", callback_data="back_search")])
        
        await query.edit_message_text(
            f"📺 **{title}**\n"
            f"Total: {len(episodes)} episodes\n\n"
            f"Episode choose karo:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data == "back_search":
        # Clear user data and ask for new search
        if 'results' in user_data:
            del user_data['results']
        if 'episodes' in user_data:
            del user_data['episodes']
        
        await query.edit_message_text(
            "🔍 **Anime name bhejo:**\n"
            "Example: `Naruto`, `One Piece`",
            parse_mode=ParseMode.MARKDOWN
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Error aagaya! Dobara try karo."
        )

# ==================== MAIN ====================

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_error_handler(error_handler)
    
    logger.info("Bot starting...")
    app.run_polling()

if __name__ == "__main__":
    try:
        main()
    finally:
        asyncio.run(scraper.close())
