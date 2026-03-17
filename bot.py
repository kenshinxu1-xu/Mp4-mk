import subprocess
import os
import re
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# API Details
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

app = Client("ani_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text(f"👋 **Ram Ram {message.from_user.first_name} Bhai!**\n\nMain ready hoon. Bas `/search [Anime Name]` likho.")

@app.on_message(filters.command("search"))
async def search_anime(client, message):
    query = " ".join(message.command[1:])
    if not query:
        return await message.reply_text("❌ Anime ka naam likho bhai!")

    status = await message.reply_text(f"🔍 **Dhoondh raha hoon:** `{query}`...")

    try:
        # FIX: Hum direct ani-cli ko bol rahe hain ki pehla result uthaye (-e 1) 
        # aur episode 1 ka link print kare (-p)
        cmd = f"ani-cli -e 1 -p '{query}'"
        
        # subprocess.run use karenge taaki timeout na ho
        process = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        result = process.stdout.strip()

        # Link nikalne ke liye Regex
        links = re.findall(r'(https?://\S+)', result)

        if links:
            # Aksar m3u8 ya mp4 link milta hai
            direct_link = links[-1]
            
            # Agar link mein 'vidsrc' ya 'gogo' hai toh wo kaam karega
            btn = InlineKeyboardMarkup([
                [InlineKeyboardButton("📺 Play Video", url=direct_link)],
                [InlineKeyboardButton("🔗 Copy Link", url=f"https://t.me/share/url?url={direct_link}")]
            ])
            
            await status.edit(
                f"✅ **Link Mil Gaya!**\n\n📌 **Anime:** `{query}`\n🔗 **Direct Link:** `{direct_link}`",
                reply_markup=btn
            )
        else:
            # Agar koi link nahi mila toh debug info dikhayega
            await status.edit(f"❌ **Link nahi mila!**\n\nHo sakta hai ye anime abhi server par na ho ya spelling galat ho.")

    except Exception as e:
        await status.edit(f"⚠️ **Error:**\n`{str(e)}`")

app.run()
