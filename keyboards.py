from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Dict, Any

def main_menu_keyboard():
    """Main menu keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("🔍 Search Anime", callback_data="menu_search"),
            InlineKeyboardButton("⭐ Favorites", callback_data="menu_favorites")
        ],
        [
            InlineKeyboardButton("📜 History", callback_data="menu_history"),
            InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings")
        ],
        [
            InlineKeyboardButton("🆕 Recent Releases", callback_data="menu_recent"),
            InlineKeyboardButton("📥 Batch Download", callback_data="menu_batch")
        ],
        [
            InlineKeyboardButton("❓ Help", callback_data="menu_help"),
            InlineKeyboardButton("ℹ️ About", callback_data="menu_about")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def anime_results_keyboard(results: List[Dict], page: int = 1, total_pages: int = 1):
    """Keyboard for anime search results"""
    keyboard = []
    
    # Add anime results
    for idx, anime in enumerate(results, 1):
        btn_text = f"{idx}. {anime['title'][:30]}"
        if anime.get('year'):
            btn_text += f" ({anime['year']})"
        
        keyboard.append([
            InlineKeyboardButton(btn_text, callback_data=f"anime_{anime['id']}")
        ])
    
    # Navigation buttons
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("◀️ Prev", callback_data=f"page_{page-1}"))
    
    nav_buttons.append(InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="page_info"))
    
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("Next ▶️", callback_data=f"page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Back to main menu
    keyboard.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
    
    return InlineKeyboardMarkup(keyboard)

def anime_detail_keyboard(anime_id: str, is_favorite: bool = False):
    """Keyboard for anime details"""
    keyboard = [
        [
            InlineKeyboardButton("📺 Watch Now", callback_data=f"watch_{anime_id}"),
            InlineKeyboardButton("📥 Download", callback_data=f"download_{anime_id}")
        ],
        [
            InlineKeyboardButton("📋 Episodes List", callback_data=f"episodes_{anime_id}_1"),
            InlineKeyboardButton("⭐ " + ("Unfavorite" if is_favorite else "Favorite"), 
                                callback_data=f"favorite_{anime_id}")
        ],
        [
            InlineKeyboardButton("🔍 Similar Anime", callback_data=f"similar_{anime_id}"),
            InlineKeyboardButton("ℹ️ More Info", callback_data=f"info_{anime_id}")
        ],
        [InlineKeyboardButton("◀️ Back to Search", callback_data="back_to_search")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def episodes_keyboard(anime_id: str, episodes: List[int], page: int = 1, 
                     episodes_per_page: int = 10, total_episodes: int = 0):
    """Keyboard for episodes list"""
    keyboard = []
    
    # Calculate range
    start = (page - 1) * episodes_per_page
    end = min(start + episodes_per_page, total_episodes)
    current_episodes = episodes[start:end]
    
    # Add episode buttons in rows of 5
    row = []
    for i, ep_num in enumerate(current_episodes, 1):
        btn = InlineKeyboardButton(
            f"Ep {ep_num}", 
            callback_data=f"ep_{anime_id}_{ep_num}"
        )
        row.append(btn)
        
        if i % 5 == 0 or i == len(current_episodes):
            keyboard.append(row)
            row = []
    
    # Navigation buttons
    nav_buttons = []
    total_pages = (total_episodes + episodes_per_page - 1) // episodes_per_page
    
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("◀️ Prev", callback_data=f"ep_page_{anime_id}_{page-1}"))
    
    nav_buttons.append(InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="page_info"))
    
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("Next ▶️", callback_data=f"ep_page_{anime_id}_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Additional options
    keyboard.append([
        InlineKeyboardButton("⬇️ Batch Download", callback_data=f"batch_{anime_id}"),
        InlineKeyboardButton("◀️ Back to Anime", callback_data=f"anime_{anime_id}")
    ])
    keyboard.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
    
    return InlineKeyboardMarkup(keyboard)

def episode_links_keyboard(anime_id: str, episode_num: int, download_links: Dict, stream_links: Dict):
    """Keyboard for episode links"""
    keyboard = []
    
    # Download links by quality
    if download_links:
        keyboard.append([InlineKeyboardButton("📥 DOWNLOAD LINKS", callback_data="download_header")])
        for quality, link in download_links.items():
            keyboard.append([
                InlineKeyboardButton(f"⬇️ {quality}", url=link)
            ])
    
    # Stream links
    if stream_links:
        keyboard.append([InlineKeyboardButton("📺 STREAM LINKS", callback_data="stream_header")])
        for quality, link in stream_links.items():
            keyboard.append([
                InlineKeyboardButton(f"▶️ {quality}", url=link)
            ])
    
    # Navigation
    keyboard.append([
        InlineKeyboardButton("◀️ Prev Ep", callback_data=f"ep_{anime_id}_{episode_num-1}"),
        InlineKeyboardButton("Next Ep ▶️", callback_data=f"ep_{anime_id}_{episode_num+1}")
    ])
    keyboard.append([
        InlineKeyboardButton("📋 Episodes List", callback_data=f"episodes_{anime_id}_1"),
        InlineKeyboardButton("◀️ Back", callback_data=f"anime_{anime_id}")
    ])
    keyboard.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
    
    return InlineKeyboardMarkup(keyboard)

def settings_keyboard(current_settings: Dict):
    """Settings keyboard"""
    keyboard = [
        [
            InlineKeyboardButton(
                f"📺 Source: {current_settings.get('source', 'gogoanime')}", 
                callback_data="setting_source"
            )
        ],
        [
            InlineKeyboardButton(
                f"🎯 Quality: {current_settings.get('quality', '720p')}", 
                callback_data="setting_quality"
            )
        ],
        [
            InlineKeyboardButton(
                f"🔊 Language: {current_settings.get('language', 'sub')}", 
                callback_data="setting_language"
            )
        ],
        [
            InlineKeyboardButton(
                "🔔 Notifications: " + ("ON" if current_settings.get('notifications', True) else "OFF"), 
                callback_data="setting_notifications"
            )
        ],
        [InlineKeyboardButton("◀️ Back", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)
