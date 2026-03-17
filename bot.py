import os
import logging
import asyncio
import aiohttp
from urllib.parse import quote, urljoin
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
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("No BOT_TOKEN found!")
    exit(1)

# Cache (30 minutes for search, 1 hour for episodes)
search_cache = TTLCache(maxsize=50, ttl=1800)
episode_cache = TTLCache(maxsize=100, ttl=3600)
link_cache = TTLCache(maxsize=200, ttl=7200)

# ==================== ANIME SOURCES CONFIGURATION ====================
SOURCES = [
    {
        'name': 'GogoAnime',
        'search_url': 'https://gogoanime3.co/search.html?keyword={}',
        'base_url': 'https://gogoanime3.co',
        'type': 'gogoanime'
    },
    {
        'name': 'AnimeDubHindi',
        'search_url': 'https://animedubhindi.me/?s={}',
        'base_url': 'https://animedubhindi.me',
        'type': 'wordpress'
    },
    {
        'name': 'AnimeSalt',
        'search_url': 'https://animesalt.top/search?q={}',
        'base_url': 'https://animesalt.top',
        'type': 'animesalt'
    },
    {
        'name': 'WatchAnimeWorld',
        'search_url': 'https://watchanimeworld.net/search?q={}',
        'base_url': 'https://watchanimeworld.net',
        'type': 'watchanimeworld'
    }
]

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
    
    async def search_anime(self, query: str) -> list:
        """Search anime across all sources"""
        cache_key = f"search_{query}"
        if cache_key in search_cache:
            return search_cache[cache_key]
        
        results = []
        session = await self.get_session()
        
        for source in SOURCES:
            try:
                search_url = source['search_url'].format(quote(query))
                logger.info(f"Searching {source['name']}: {search_url}")
                async with session.get(search_url, timeout=15) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        soup = BeautifulSoup(html, 'lxml')
                        
                        if source['type'] == 'gogoanime':
                            items = soup.select('div.img a')[:8]
                            for item in items:
                                title = item.get('title', '').strip()
                                if title:
                                    results.append({
                                        'title': title,
                                        'url': urljoin(source['base_url'], item.get('href', '')),
                                        'source': source['name'],
                                        'source_key': source['type'],
                                        'id': item.get('href', '').split('/')[-1]
                                    })
                        
                        elif source['type'] == 'wordpress':
                            items = soup.select('article h2 a')[:8]
                            for item in items:
                                title = item.text.strip()
                                if title:
                                    results.append({
                                        'title': title,
                                        'url': item.get('href', ''),
                                        'source': source['name'],
                                        'source_key': source['type']
                                    })
                        
                        elif source['type'] == 'animesalt':
                            items = soup.select('a.block')[:8]
                            for item in items:
                                title_tag = item.select_one('h3')
                                if title_tag:
                                    title = title_tag.text.strip()
                                    if title:
                                        results.append({
                                            'title': title,
                                            'url': urljoin(source['base_url'], item.get('href', '')),
                                            'source': source['name'],
                                            'source_key': source['type']
                                        })
                        
                        elif source['type'] == 'watchanimeworld':
                            items = soup.select('a.relative')[:8]
                            for item in items:
                                title_tag = item.select_one('h3')
                                if title_tag:
                                    title = title_tag.text.strip()
                                    if title:
                                        results.append({
                                            'title': title,
                                            'url': urljoin(source['base_url'], item.get('href', '')),
                                            'source': source['name'],
                                            'source_key': source['type']
                                        })
            except Exception as e:
                logger.error(f"Error searching {source['name']}: {e}")
                continue
        
        # Remove duplicates by title (simple)
        seen = set()
        unique_results = []
        for r in results:
            if r['title'] not in seen:
                seen.add(r['title'])
                unique_results.append(r)
        
        search_cache[cache_key] = unique_results
        return unique_results
    
    async def get_episodes(self, anime_url: str, source_type: str) -> list:
        """Get episodes list from anime page"""
        cache_key = f"eps_{anime_url}"
        if cache_key in episode_cache:
            return episode_cache[cache_key]
        
        episodes = []
        session = await self.get_session()
        
        try:
            async with session.get(anime_url, timeout=15) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'lxml')
                    
                    if source_type == 'gogoanime':
                        ep_links = soup.select('ul#episode_related li a')
                        for link in ep_links:
                            ep_text = link.text.strip().replace('EP', '').strip()
                            if ep_text.isdigit():
                                episodes.append({
                                    'number': int(ep_text),
                                    'url': urljoin('https://gogoanime3.co', link.get('href', ''))
                                })
                        # Sort by number
                        episodes.sort(key=lambda x: x['number'])
                    
                    elif source_type == 'wordpress':
                        ep_links = soup.select('div.eplister a')
                        for link in ep_links[:50]:
                            ep_num = link.select_one('.epl-num')
                            if ep_num and ep_num.text.strip().isdigit():
                                episodes.append({
                                    'number': int(ep_num.text.strip()),
                                    'url': link.get('href', '')
                                })
                        episodes.sort(key=lambda x: x['number'])
                    
                    elif source_type == 'animesalt':
                        ep_links = soup.select('a.episode-link')
                        for i, link in enumerate(ep_links[:50], 1):
                            episodes.append({
                                'number': i,
                                'url': urljoin('https://animesalt.top', link.get('href', ''))
                            })
                    
                    elif source_type == 'watchanimeworld':
                        ep_links = soup.select('a.episode')
                        for link in ep_links[:50]:
                            ep_num = link.select_one('span.ep-number')
                            if ep_num:
                                num = ep_num.text.strip().replace('Episode', '').strip()
                                if num.isdigit():
                                    episodes.append({
                                        'number': int(num),
                                        'url': urljoin('https://watchanimeworld.net', link.get('href', ''))
                                    })
                        episodes.sort(key=lambda x: x['number'])
            # Limit to 100 episodes max
            episodes = episodes[:100]
        except Exception as e:
            logger.error(f"Error getting episodes from {anime_url}: {e}")
        
        episode_cache[cache_key] = episodes
        return episodes
    
    async def get_download_links(self, episode_url: str, source_type: str) -> dict:
        """Extract download links from episode page"""
        cache_key = f"links_{episode_url}"
        if cache_key in link_cache:
            return link_cache[cache_key]
        
        links = {}
        session = await self.get_session()
        
        try:
            async with session.get(episode_url, timeout=15) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'lxml')
                    
                    # Common patterns across sites
                    # Look for download links section
                    download_section = soup.find('div', class_='download-links') or \
                                       soup.find('div', class_='mirror_link') or \
                                       soup.find('div', class_='dowload') or \
                                       soup.find('div', {'id': 'download'})
                    
                    if download_section:
                        for a in download_section.find_all('a', href=True):
                            text = a.text.lower()
                            href = a['href']
                            if '1080' in text or '1080p' in text:
                                links['1080p'] = href
                            elif '720' in text or '720p' in text:
                                links['720p'] = href
                            elif '480' in text or '480p' in text:
                                links['480p'] = href
                            elif '360' in text or '360p' in text:
                                links['360p'] = href
                            elif 'mp4' in href and 'quality' not in links:
                                links['Direct'] = href
                    
                    # If still no links, try to find video source
                    if not links:
                        video = soup.find('video')
                        if video and video.find('source'):
                            src = video.find('source').get('src', '')
                            if src:
                                links['Stream'] = src
                    
                    # For gogoanime, sometimes links are in iframe
                    if not links:
                        iframe = soup.find('iframe', src=True)
                        if iframe:
                            # Could be stream, but we need to follow redirects
                            # For simplicity, store the iframe src as stream link
                            links['Stream'] = urljoin(episode_url, iframe['src'])
        except Exception as e:
            logger.error(f"Error getting download links from {episode_url}: {e}")
        
        link_cache[cache_key] = links
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
        f"🔍 **Bas anime name bhejo** – main multiple sites se search karunga:\n"
        f"• GogoAnime\n"
        f"• AnimeDubHindi\n"
        f"• AnimeSalt\n"
        f"• WatchAnimeWorld\n\n"
        f"Example: `Naruto`, `One Piece`, `Jujutsu Kaisen`\n\n"
        f"✅ Results site name ke saath dikhenge!",
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    
    if query.startswith('/') or len(query) < 3:
        return
    
    msg = await update.message.reply_text(f"🔍 `{query}` search kar raha hoon... (4 sites check karunga)")
    
    results = await scraper.search_anime(query)
    
    if not results:
        await msg.edit_text(
            f"❌ `{query}` ke liye koi result nahi mila!\n\n"
            f"💡 Tips:\n"
            f"• Spelling check karo\n"
            f"• English name try karo\n"
            f"• Full name use karo (e.g., 'Naruto Shippuden')",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Store results in context for callback
    context.user_data['search_results'] = results
    context.user_data['search_query'] = query
    
    # Create inline keyboard with long buttons
    keyboard = []
    for idx, anime in enumerate(results[:10], 1):
        # Display title with site name in brackets
        btn_text = f"{idx}. [{anime['source']}] {anime['title'][:30]}"
        keyboard.append([
            InlineKeyboardButton(btn_text, callback_data=f"anime_{idx-1}")
        ])
    
    await msg.edit_text(
        f"📺 **{len(results)} results mile:**\n\n"
        f"Apni pasand ka anime choose karo 👇",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_data = context.user_data
    
    if data.startswith('anime_'):
        idx = int(data.replace('anime_', ''))
        results = user_data.get('search_results', [])
        if idx >= len(results):
            await query.edit_message_text("❌ Invalid selection! Dobara search karo.")
            return
        
        anime = results[idx]
        user_data['current_anime'] = anime
        
        await query.edit_message_text(
            f"📺 **{anime['title']}**\n"
            f"🔗 Source: {anime['source']}\n\n"
            f"📥 Episodes fetch kar raha hoon...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        episodes = await scraper.get_episodes(anime['url'], anime.get('source_key', 'gogoanime'))
        
        if not episodes:
            await query.edit_message_text(
                f"❌ Episodes nahi mile!\n{anime['url']}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("◀️ Wapas search", callback_data="back_search")
                ]])
            )
            return
        
        user_data['episodes'] = episodes
        
        # Create episode keyboard (5 per row, long buttons)
        keyboard = []
        row = []
        for i, ep in enumerate(episodes[:30], 1):  # Show first 30 episodes
            btn = InlineKeyboardButton(f"Ep {ep['number']}", callback_data=f"ep_{i-1}")
            row.append(btn)
            if len(row) == 5:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("◀️ Wapas search", callback_data="back_search")])
        
        await query.edit_message_text(
            f"📺 **{anime['title']}**\n"
            f"Total episodes: {len(episodes)}\n\n"
            f"Episode choose karo:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data.startswith('ep_'):
        idx = int(data.replace('ep_', ''))
        episodes = user_data.get('episodes', [])
        anime = user_data.get('current_anime', {})
        
        if idx >= len(episodes):
            await query.edit_message_text("❌ Episode not found!")
            return
        
        ep = episodes[idx]
        
        await query.edit_message_text(
            f"🔍 Download links fetch kar raha hoon...\n{ep['url']}",
            parse_mode=ParseMode.MARKDOWN
        )
        
        links = await scraper.get_download_links(ep['url'], anime.get('source_key', 'gogoanime'))
        
        if not links:
            await query.edit_message_text(
                f"❌ Is episode ke liye links nahi mile!\n{ep['url']}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("◀️ Wapas episodes", callback_data="back_ep")
                ]])
            )
            return
        
        # Create buttons for each link
        keyboard = []
        for quality, url in links.items():
            btn_text = f"⬇️ {quality}"
            keyboard.append([InlineKeyboardButton(btn_text, url=url)])
        
        keyboard.append([
            InlineKeyboardButton("◀️ Wapas episodes", callback_data="back_ep"),
            InlineKeyboardButton("🔍 New search", callback_data="back_search")
        ])
        
        title = anime.get('title', 'Anime')
        await query.edit_message_text(
            f"📺 **{title} - Episode {ep['number']}**\n\n"
            f"✅ {len(links)} links mil gaye:\n"
            f"• Site: {anime.get('source', 'Unknown')}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
    
    elif data == "back_ep":
        # Go back to episodes list
        episodes = user_data.get('episodes', [])
        anime = user_data.get('current_anime', {})
        
        keyboard = []
        row = []
        for i, ep in enumerate(episodes[:30], 1):
            btn = InlineKeyboardButton(f"Ep {ep['number']}", callback_data=f"ep_{i-1}")
            row.append(btn)
            if len(row) == 5:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("◀️ Wapas search", callback_data="back_search")])
        
        await query.edit_message_text(
            f"📺 **{anime.get('title', 'Anime')}**\n"
            f"Total episodes: {len(episodes)}\n\n"
            f"Episode choose karo:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data == "back_search":
        # Clear relevant data and ask for new search
        user_data.pop('search_results', None)
        user_data.pop('episodes', None)
        user_data.pop('current_anime', None)
        await query.edit_message_text(
            "🔍 **Anime name bhejo:**\n"
            "Example: `Naruto`, `One Piece`, `Jujutsu Kaisen`",
            parse_mode=ParseMode.MARKDOWN
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ Kuch technical error aagaya! Dobara try karo."
            )
    except:
        pass

# ==================== MAIN ====================

async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_error_handler(error_handler)
    
    logger.info("Bot starting... Press Ctrl+C to stop.")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    # Keep running
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        logger.info("Stopping bot...")
    finally:
        await app.stop()
        await app.shutdown()
        await scraper.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
