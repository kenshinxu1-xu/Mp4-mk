import os
import logging
import asyncio
import aiohttp
import re
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

# Cache
search_cache = TTLCache(maxsize=50, ttl=1800)
episode_cache = TTLCache(maxsize=100, ttl=3600)
link_cache = TTLCache(maxsize=200, ttl=7200)

# ==================== SITE CONFIGURATIONS ====================
SITES = [
    {
        'name': '✨ AnimeDubHindi',
        'search_url': 'https://animedubhindi.me/?s={}',
        'base_url': 'https://animedubhindi.me',
        'type': 'wordpress',
        'search_selector': 'article h2 a',
        'episode_selector': 'div.eplister a',
        'download_selector': 'div.download-links a, div.mirror_link a, a[href*="drive.google"], a[href*="mega.nz"]'
    },
    {
        'name': '⚡ GogoAnime',
        'search_url': 'https://gogoanime3.co/search.html?keyword={}',
        'base_url': 'https://gogoanime3.co',
        'type': 'gogoanime',
        'search_selector': 'div.img a',
        'episode_selector': 'ul#episode_related li a',
        'download_selector': 'div.download-links a'
    },
    {
        'name': '🌊 AnimeSalt',
        'search_url': 'https://animesalt.top/search?q={}',
        'base_url': 'https://animesalt.top',
        'type': 'animesalt',
        'search_selector': 'a.block',
        'title_selector': 'h3',
        'episode_selector': 'a.episode-link',
        'download_selector': 'a[href*="download"], a[href*="drive"], a[href*="mega"]'
    },
    {
        'name': '🎬 WatchAnimeWorld',
        'search_url': 'https://watchanimeworld.net/search?q={}',
        'base_url': 'https://watchanimeworld.net',
        'type': 'watchanimeworld',
        'search_selector': 'a.relative',
        'title_selector': 'h3',
        'episode_selector': 'a.episode',
        'download_selector': 'a.download-link, a[href*="drive"]'
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
        """Search across all sites"""
        cache_key = f"search_{query}"
        if cache_key in search_cache:
            return search_cache[cache_key]
        
        results = []
        session = await self.get_session()
        
        for site in SITES:
            try:
                search_url = site['search_url'].format(quote(query))
                logger.info(f"🔍 Searching {site['name']}: {search_url}")
                
                async with session.get(search_url, timeout=15) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        soup = BeautifulSoup(html, 'lxml')
                        
                        # Site-specific search parsing
                        items = soup.select(site['search_selector'])[:5]
                        
                        for item in items:
                            if site['type'] == 'gogoanime':
                                title = item.get('title', '').strip()
                                link = item.get('href', '')
                            elif site['type'] == 'wordpress':
                                title = item.text.strip()
                                link = item.get('href', '')
                            elif site['type'] in ['animesalt', 'watchanimeworld']:
                                title_sel = site.get('title_selector', 'h3')
                                title_tag = item.select_one(title_sel)
                                title = title_tag.text.strip() if title_tag else ''
                                link = item.get('href', '')
                            
                            if title and link:
                                results.append({
                                    'title': title,
                                    'url': urljoin(site['base_url'], link),
                                    'site': site['name'],
                                    'site_type': site['type']
                                })
            except Exception as e:
                logger.error(f"❌ Error searching {site['name']}: {e}")
                continue
        
        # Remove duplicates
        seen = set()
        unique_results = []
        for r in results:
            if r['title'] not in seen:
                seen.add(r['title'])
                unique_results.append(r)
        
        search_cache[cache_key] = unique_results
        return unique_results
    
    async def get_episodes_or_movie(self, url: str, site_type: str) -> dict:
        """Check if it's a movie or series and get episodes/downloads"""
        cache_key = f"content_{url}"
        if cache_key in episode_cache:
            return episode_cache[cache_key]
        
        result = {
            'type': 'unknown',
            'title': '',
            'episodes': [],
            'direct_links': []
        }
        
        session = await self.get_session()
        
        try:
            async with session.get(url, timeout=15) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'lxml')
                    
                    # Get title
                    title_tag = soup.find('h1') or soup.find('title')
                    result['title'] = title_tag.text.strip() if title_tag else 'Unknown'
                    
                    # Check if it's a movie (look for movie indicators)
                    is_movie = False
                    movie_indicators = ['movie', 'film', '480p', '720p', '1080p', 'bluray', 'hdrip']
                    page_text = soup.get_text().lower()
                    
                    if any(indicator in page_text for indicator in movie_indicators):
                        is_movie = True
                    
                    # Try to find episodes first
                    episodes = []
                    site_config = next((s for s in SITES if s['type'] == site_type), None)
                    
                    if site_config and 'episode_selector' in site_config and not is_movie:
                        ep_links = soup.select(site_config['episode_selector'])[:50]
                        for link in ep_links:
                            ep_text = link.text.strip()
                            ep_url = urljoin(url, link.get('href', ''))
                            
                            # Try to extract episode number
                            ep_num = None
                            numbers = re.findall(r'\d+', ep_text)
                            if numbers:
                                ep_num = int(numbers[0])
                            
                            episodes.append({
                                'number': ep_num if ep_num else len(episodes) + 1,
                                'url': ep_url,
                                'text': ep_text[:30]
                            })
                    
                    if episodes:
                        result['type'] = 'series'
                        result['episodes'] = episodes[:50]
                    else:
                        # No episodes found - treat as movie, find direct download links
                        result['type'] = 'movie'
                        
                        # Find all potential download links
                        site_config = next((s for s in SITES if s['type'] == site_type), None)
                        download_selectors = site_config.get('download_selector', 'a[href*="drive"], a[href*="mega"], a[href*="mediafire"]')
                        
                        # Common download link patterns
                        patterns = [
                            r'https?://(?:drive\.google\.com|mega\.nz|mediafire\.com)[^\s"<>]+',
                            r'https?://[^\s"<>]+\.(?:mp4|mkv|avi|mov)[^\s"<>]*'
                        ]
                        
                        # Find using selectors
                        for selector in download_selectors.split(','):
                            links = soup.select(selector.strip())
                            for link in links:
                                href = link.get('href', '')
                                if href and not href.startswith('#'):
                                    result['direct_links'].append({
                                        'text': link.text.strip()[:30] or 'Download Link',
                                        'url': urljoin(url, href)
                                    })
                        
                        # Find using regex patterns
                        for pattern in patterns:
                            matches = re.findall(pattern, html)
                            for match in matches[:3]:  # Limit to 3 matches
                                result['direct_links'].append({
                                    'text': 'Direct Download',
                                    'url': match
                                })
                        
                        # Remove duplicates
                        seen_urls = set()
                        unique_links = []
                        for link in result['direct_links']:
                            if link['url'] not in seen_urls:
                                seen_urls.add(link['url'])
                                unique_links.append(link)
                        result['direct_links'] = unique_links[:5]
        
        except Exception as e:
            logger.error(f"❌ Error fetching content from {url}: {e}")
        
        episode_cache[cache_key] = result
        return result
    
    async def get_download_links(self, episode_url: str, site_type: str) -> dict:
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
                    
                    # Site-specific download link extraction
                    site_config = next((s for s in SITES if s['type'] == site_type), None)
                    
                    if site_config and 'download_selector' in site_config:
                        download_links = soup.select(site_config['download_selector'])
                        for link in download_links[:5]:
                            text = link.text.lower()
                            href = link.get('href', '')
                            if '1080' in text or '1080p' in text:
                                links['1080p'] = href
                            elif '720' in text or '720p' in text:
                                links['720p'] = href
                            elif '480' in text or '480p' in text:
                                links['480p'] = href
                            elif '360' in text or '360p' in text:
                                links['360p'] = href
                            elif 'drive' in href or 'mega' in href:
                                links['GDrive/Mega'] = href
                            else:
                                links[text[:10]] = href
                    
                    # Generic fallback - find any video/download links
                    if not links:
                        video_patterns = [
                            r'https?://[^\s"<>]+\.(?:mp4|mkv|avi|mov)[^\s"<>]*',
                            r'https?://[^\s"<>]*drive\.google\.com[^\s"<>]+',
                            r'https?://[^\s"<>]*mega\.nz[^\s"<>]+'
                        ]
                        for pattern in video_patterns:
                            matches = re.findall(pattern, html)
                            for i, match in enumerate(matches[:3]):
                                links[f'Link {i+1}'] = match
        except Exception as e:
            logger.error(f"❌ Error getting links from {episode_url}: {e}")
        
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
        f"Main **Anime Download Bot** hoon - Real Working!\n\n"
        f"🔍 **Bas anime name bhejo** – main 4 sites se search karunga:\n"
        f"{chr(10).join([f'• {site}' for site in ['✨ AnimeDubHindi', '⚡ GogoAnime', '🌊 AnimeSalt', '🎬 WatchAnimeWorld']])}\n\n"
        f"✅ **Movies aur Series** dono handle karta hoon!\n"
        f"✅ **Real download links** - GDrive, Mega, Direct\n\n"
        f"Example: `Jujutsu Kaisen`, `Naruto`, `One Piece`",
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    
    if query.startswith('/') or len(query) < 3:
        return
    
    msg = await update.message.reply_text(f"🔍 `{query}` search kar raha hoon... (4 sites check kar raha hoon)")
    
    results = await scraper.search_anime(query)
    
    if not results:
        await msg.edit_text(
            f"❌ `{query}` ke liye koi result nahi mila!\n\n"
            f"💡 Tips:\n"
            f"• Spelling check karo\n"
            f"• English name try karo\n"
            f"• Short name try karo (e.g., 'JJK' for Jujutsu Kaisen)",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Store results
    context.user_data['search_results'] = results
    
    # Create keyboard
    keyboard = []
    for idx, anime in enumerate(results[:10], 1):
        btn_text = f"{idx}. {anime['site']} - {anime['title'][:25]}"
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
            f"📌 Site: {anime['site']}\n\n"
            f"🔄 Content fetch kar raha hoon...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        content = await scraper.get_episodes_or_movie(anime['url'], anime['site_type'])
        
        if content['type'] == 'series' and content['episodes']:
            user_data['episodes'] = content['episodes']
            
            # Create episode keyboard
            keyboard = []
            row = []
            for i, ep in enumerate(content['episodes'][:30], 1):
                btn = InlineKeyboardButton(f"Ep {ep['number']}", callback_data=f"ep_{i-1}")
                row.append(btn)
                if len(row) == 5:
                    keyboard.append(row)
                    row = []
            if row:
                keyboard.append(row)
            
            keyboard.append([InlineKeyboardButton("◀️ Wapas search", callback_data="back_search")])
            
            await query.edit_message_text(
                f"📺 **{content['title']}**\n"
                f"Total episodes: {len(content['episodes'])}\n\n"
                f"Episode choose karo:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
        
        elif content['type'] == 'movie' and content['direct_links']:
            # Show movie download links directly
            keyboard = []
            for link in content['direct_links'][:5]:
                keyboard.append([InlineKeyboardButton(f"📥 {link['text']}", url=link['url'])])
            
            keyboard.append([InlineKeyboardButton("◀️ Wapas search", callback_data="back_search")])
            
            await query.edit_message_text(
                f"🎬 **{content['title']}**\n"
                f"Type: Movie\n\n"
                f"✅ {len(content['direct_links'])} download links mile:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
        
        else:
            await query.edit_message_text(
                f"❌ Is page se kuch nahi mila!\n{anime['url']}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("◀️ Wapas search", callback_data="back_search")
                ]])
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
            f"🔍 Download links fetch kar raha hoon...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        links = await scraper.get_download_links(ep['url'], anime['site_type'])
        
        if not links:
            await query.edit_message_text(
                f"❌ Is episode ke liye links nahi mile!\n{ep['url']}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("◀️ Wapas episodes", callback_data="back_ep")
                ]])
            )
            return
        
        keyboard = []
        for quality, url in links.items():
            btn_text = f"⬇️ {quality}"
            keyboard.append([InlineKeyboardButton(btn_text, url=url)])
        
        keyboard.append([
            InlineKeyboardButton("◀️ Wapas episodes", callback_data="back_ep"),
            InlineKeyboardButton("🔍 New search", callback_data="back_search")
        ])
        
        await query.edit_message_text(
            f"📺 **{anime.get('title', 'Anime')} - Episode {ep['number']}**\n\n"
            f"✅ {len(links)} links mil gaye:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
    
    elif data == "back_ep":
        # Go back to episodes
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
        user_data.pop('search_results', None)
        user_data.pop('episodes', None)
        user_data.pop('current_anime', None)
        await query.edit_message_text(
            "🔍 **Anime name bhejo:**\n"
            "Example: `Jujutsu Kaisen`, `Naruto`, `One Piece`",
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
    
    logger.info("🤖 Bot starting... Press Ctrl+C to stop.")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        logger.info("🛑 Stopping bot...")
    finally:
        await app.stop()
        await app.shutdown()
        await scraper.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
