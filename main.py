#!/usr/bin/env python3
import asyncio
import logging
from bot import bot
from scraper import scraper

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def main():
    """Main function"""
    try:
        # Start bot
        print("🤖 Anime Bot is starting...")
        bot.run()
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        # Cleanup
        await scraper.close()

if __name__ == "__main__":
    asyncio.run(main())
