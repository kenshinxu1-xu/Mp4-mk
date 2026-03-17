import os
from dotenv import load_dotenv

load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("No BOT_TOKEN found in environment variables")

# API Configuration
GOGOANIME_URL = "https://gogoanime3.co"
ZORO_URL = "https://zoro.to"

# Bot Settings
MAX_EPISODES_PER_PAGE = 10
CACHE_TIMEOUT = 3600  # 1 hour
RESULTS_PER_PAGE = 5

# User Agents
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
