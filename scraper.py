import aiohttp
import asyncio
from typing import List, Dict, Optional, Tuple
from bs4 import BeautifulSoup
import re
from py_anidl import AniDL
from ani_scrapy import GogoAnime, Zoro
from utils import clean_anime_name, search_cache, episode_cache
from config import GOGOANIME_URL, ZORO_URL, USER_AGENT

class AnimeScraper:
    def __init__(self):
        self.anidl = AniDL()
        self.gogo = GogoAnime()
        self.zoro = Zoro()
        self.session = None
    
    async def get_session(self):
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(headers={'User-Agent': USER_AGENT})
        return self.session
    
    async def search_anime(self, query: str, source: str = 'gogoanime') -> List[Dict]:
        """Search anime by name"""
        cache_key = f"{source}_{query}"
        if cache_key in search_cache:
            return search_cache[cache_key]
        
        results = []
        clean_query = clean_anime_name(query)
        
        try:
            if source == 'gogoanime':
                # Search using ani-scrapy
                gogo_results = self.gogo.search(query)
                for res in gogo_results[:10]:  # Limit to 10 results
                    results.append({
                        'id': res.get('id', ''),
                        'title': res.get('title', 'Unknown'),
                        'url': res.get('url', ''),
                        'image': res.get('image', ''),
                        'year': res.get('year', ''),
                        'status': res.get('status', 'Unknown'),
                        'source': 'gogoanime'
                    })
            
            elif source == 'zoro':
                # Search using Zoro
                async with await self.get_session() as session:
                    url = f"{ZORO_URL}/search?keyword={clean_query}"
                    async with session.get(url) as response:
                        if response.status == 200:
                            html = await response.text()
                            soup = BeautifulSoup(html, 'html.parser')
                            # Parse Zoro results
                            # (Add Zoro parsing logic here)
                            pass
            
            # Also try PyAniDL for more results
            try:
                py_results = self.anidl.search(query)
                for res in py_results:
                    if not any(r['title'] == res.title for r in results):
                        results.append({
                            'id': res.id,
                            'title': res.title,
                            'url': res.url,
                            'image': res.image,
                            'year': res.year,
                            'episodes': res.episode_count,
                            'source': 'py-anidl'
                        })
            except:
                pass
            
        except Exception as e:
            print(f"Search error: {e}")
        
        search_cache[cache_key] = results
        return results
    
    async def get_anime_details(self, anime_id: str, source: str = 'gogoanime') -> Dict:
        """Get detailed anime information"""
        details = {
            'id': anime_id,
            'title': 'Unknown',
            'description': '',
            'genre': [],
            'year': '',
            'status': '',
            'episodes': [],
            'total_episodes': 0,
            'image': '',
            'rating': ''
        }
        
        try:
            if source == 'gogoanime':
                # Get from GogoAnime
                anime_info = self.gogo.get_anime_info(anime_id)
                if anime_info:
                    details.update(anime_info)
                    
                    # Get episodes
                    episodes = self.gogo.get_episodes(anime_id)
                    details['episodes'] = [ep['number'] for ep in episodes]
                    details['total_episodes'] = len(episodes)
            
            elif source == 'py-anidl':
                # Get from PyAniDL
                anime = self.anidl.get_anime(anime_id)
                if anime:
                    details['title'] = anime.title
                    details['description'] = anime.description
                    details['genre'] = anime.genre
                    details['year'] = anime.year
                    details['status'] = anime.status
                    details['episodes'] = list(range(1, anime.episode_count + 1))
                    details['total_episodes'] = anime.episode_count
                    details['image'] = anime.image
                    details['rating'] = anime.rating
            
        except Exception as e:
            print(f"Details error: {e}")
        
        return details
    
    async def get_episode_links(self, anime_id: str, episode_num: int, 
                               source: str = 'gogoanime') -> Tuple[Dict, Dict]:
        """Get download and stream links for episode"""
        cache_key = f"{source}_{anime_id}_ep{episode_num}"
        if cache_key in episode_cache:
            return episode_cache[cache_key]
        
        download_links = {}
        stream_links = {}
        
        try:
            if source == 'gogoanime':
                # Get from GogoAnime
                episode_data = self.gogo.get_episode(anime_id, episode_num)
                if episode_data:
                    # Extract download links
                    for quality, link in episode_data.get('download_links', {}).items():
                        download_links[quality] = link
                    
                    # Extract stream links
                    for quality, link in episode_data.get('stream_links', {}).items():
                        stream_links[quality] = link
            
            elif source == 'py-anidl':
                # Get from PyAniDL
                episode = self.anidl.get_episode(anime_id, episode_num)
                if episode:
                    # PyAniDL usually gives direct download links
                    download_links['Direct'] = episode.download_link
                    
                    # Try to get stream link
                    if hasattr(episode, 'stream_link'):
                        stream_links['Stream'] = episode.stream_link
            
            # If no links found, try alternative sources
            if not download_links and not stream_links:
                # Try scraping directly
                async with await self.get_session() as session:
                    # Construct GogoAnime episode URL
                    ep_url = f"{GOGOANIME_URL}/{anime_id}-episode-{episode_num}"
                    async with session.get(ep_url) as response:
                        if response.status == 200:
                            html = await response.text()
                            soup = BeautifulSoup(html, 'html.parser')
                            
                            # Extract download links
                            download_div = soup.find('div', class_='download-links')
                            if download_div:
                                for link in download_div.find_all('a'):
                                    quality = link.text.strip()
                                    if any(q in quality.lower() for q in ['360', '480', '720', '1080']):
                                        download_links[quality] = link.get('href')
                            
                            # Extract stream links
                            stream_div = soup.find('div', class_='anime_video_body')
                            if stream_div:
                                stream_url = stream_div.find('iframe')
                                if stream_url:
                                    stream_links['Stream'] = stream_url.get('src')
            
        except Exception as e:
            print(f"Episode links error: {e}")
        
        result = (download_links, stream_links)
        episode_cache[cache_key] = result
        return result
    
    async def get_recent_episodes(self, limit: int = 10) -> List[Dict]:
        """Get recently released episodes"""
        recent = []
        
        try:
            # Get from GogoAnime
            recent_eps = self.gogo.get_recent_episodes(limit)
            for ep in recent_eps:
                recent.append({
                    'anime_id': ep.get('anime_id'),
                    'anime_title': ep.get('title'),
                    'episode': ep.get('episode'),
                    'url': ep.get('url'),
                    'time': ep.get('time')
                })
        except Exception as e:
            print(f"Recent episodes error: {e}")
        
        return recent
    
    async def get_similar_anime(self, anime_id: str) -> List[Dict]:
        """Get similar anime recommendations"""
        similar = []
        
        try:
            # Get recommendations from PyAniDL
            recommendations = self.anidl.get_recommendations(anime_id)
            for rec in recommendations[:5]:
                similar.append({
                    'id': rec.get('id'),
                    'title': rec.get('title'),
                    'image': rec.get('image'),
                    'rating': rec.get('rating')
                })
        except Exception as e:
            print(f"Similar anime error: {e}")
        
        return similar
    
    async def close(self):
        """Close session"""
        if self.session and not self.session.closed:
            await self.session.close()

# Global scraper instance
scraper = AnimeScraper()
