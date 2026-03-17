import subprocess
import os
import re
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# API Details (Railway/Termux Environment Variables se uthayega)
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

app = Client("ani_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- Commands ---

@app.on_message(filters.command("start"))
async def start(client, message):
    user_name = message.from_user.first_name
    welcome_text = (
        f"👋 **Ram Ram {user_name} Bhai!**\n\n"
        "Main ek fast Anime Search Bot hoon. Bas niche di gayi command use karo:\n\n"
        "🔹 `/search [Anime Name] Hindi` - Anime dhoondhne ke liye.\n"
        "🔹 `/help` - Sabhi commands dekhne ke liye."
    )
    # Reply to the user's message
    await message.reply_text(welcome_text)

@app.on_message(filters.command("help"))
async def help_cmd(client, message):
    help_text = (
        "📖 **Kaise use karein?**\n\n"
        "1. Likho: `/search Naruto Hindi`\n"
        "2. Thoda wait karo (Scraping...)\n"
        "3. Main aapko direct Streaming Link dunga.\n\n"
        "💡 *Tip: Hindi Dub ke liye 'Hindi' zaroor likhein.*"
    )
    await message.reply_text(help_text)

@app.on_message(filters.command("search"))
async def search_anime(client, message):
    # User ne kya search kiya wo nikalna
    query = " ".join(message.command[1:])
    
    if not query:
        return await message.reply_text("❌ **Bhai, anime ka naam toh likho!**\nExample: `/search Solo Leveling Hindi`")

    status = await message.reply_text(f"🔍 **Dhoondh raha hoon:** `{query}`\n*Please wait...*")

    try:
        # ani-cli -p (print mode) se direct link nikalna
        # Hum pehla result (index 1) automate kar rahe hain
        cmd = f"printf '1\n1\n' | ani-cli -p '{query}'"
        result = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()

        # Link ko clean karna (sirf http wala part nikalna)
        links = re.findall(r'(https?://\S+)', result)
        
        if links:
            direct_link = links[-1] # Aksar aakhri link main video file hoti hai
            
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("📺 Play in VLC/MX", url=f"vlc://{direct_link}")],
                [InlineKeyboardButton("🔗 Copy Direct Link", url=f"https://t.me/share/url?url={direct_link}")]
            ])
            
            await status.edit(
                f"✅ **Anime Mil Gaya!**\n\n"
                f"📌 **Search:** `{query}`\n"
                f"🌐 **Direct Link:** `{direct_link}`\n\n"
                f"💡 *Copy karke kisi bhi player ya browser mein paste karein.*",
                reply_markup=buttons
            )
        else:
            await status.edit("❌ **Sorry bhai!** Is naam se koi link nahi mila. Thoda alag naam try karo.")

    except Exception as e:
        await status.edit(f"⚠️ **Error Aa Gaya:**\n`{str(e)}`")

print("Bot is starting...")
app.run()
