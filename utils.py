import re
import html
from typing import List, Dict, Optional
from cachetools import TTLCache
from config import CACHE_TIMEOUT

# Cache for search results
search_cache = TTLCache(maxsize=100, ttl=CACHE_TIMEOUT)
episode_cache = TTLCache(maxsize=200, ttl=CACHE_TIMEOUT)

def clean_anime_name(name: str) -> str:
    """Clean anime name for searching"""
    # Remove special characters
    name = re.sub(r'[^\w\s-]', '', name)
    # Convert to lowercase
    name = name.lower().strip()
    # Replace spaces with hyphens
    name = re.sub(r'[-\s]+', '-', name)
    return name

def format_size(size_in_bytes: int) -> str:
    """Format file size"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.1f} {unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.1f} TB"

def extract_episode_number(text: str) -> Optional[int]:
    """Extract episode number from text"""
    match = re.search(r'episode\s*(\d+)', text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None

def safe_html_text(text: str) -> str:
    """Escape HTML special characters"""
    return html.escape(str(text))

def paginate_list(items: List, page: int, per_page: int = 10):
    """Paginate any list"""
    start = (page - 1) * per_page
    end = start + per_page
    return items[start:end], len(items) > end

def get_quality_from_text(text: str) -> str:
    """Extract quality from text"""
    qualities = ['1080p', '720p', '480p', '360p']
    for quality in qualities:
        if quality in text.lower():
            return quality
    return 'Unknown'
