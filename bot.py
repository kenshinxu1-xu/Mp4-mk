import os
import re
import time
import asyncio
import subprocess
from pyrogram import Client, filters
from pyrogram.types import Message

# 🔐 ENV VARIABLES
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

bot = Client("ultimate_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# 📊 Progress bar
def progress_bar(p):
    filled = int(p // 5)
    return "█" * filled + "░" * (20 - filled)

# ⏱ time convert
def time_to_seconds(t):
    try:
        h, m, s = t.split(":")
        return float(h)*3600 + float(m)*60 + float(s)
    except:
        return 0

# 📥📤 Telegram progress
async def tg_progress(current, total, msg, start, text):
    percent = current * 100 / total if total else 0
    elapsed = time.time() - start
    speed = current / elapsed if elapsed > 0 else 0
    eta = (total - current) / speed if speed > 0 else 0

    try:
        await msg.edit_text(
            f"{text}\n\n"
            f"[{progress_bar(percent)}] {percent:.1f}%\n"
            f"🚀 {speed/1024/1024:.2f} MB/s\n"
            f"⏱ ETA: {int(eta)} sec"
        )
    except:
        pass

# ⚙️ CONVERSION WITH REAL PROGRESS
async def convert_video(input_file, output_file, duration, msg):
    cmd = [
        "ffmpeg",
        "-i", input_file,
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "30",
        "-threads", "2",
        "-c:a", "copy",
        "-progress", "pipe:1",
        "-nostats",
        output_file
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE
    )

    start = time.time()
    last_update = 0

    while True:
        line = await process.stdout.readline()
        if not line:
            break

        line = line.decode().strip()

        if "out_time=" in line:
            time_str = line.split("=")[1]
            current = time_to_seconds(time_str)

            percent = min((current / duration) * 100, 100) if duration > 0 else 0

            elapsed = time.time() - start
            speed = current / elapsed if elapsed > 0 else 0
            eta = (duration - current) / speed if speed > 0 else 0

            if time.time() - last_update > 2:
                last_update = time.time()

                try:
                    await msg.edit_text(
                        f"⚙️ Converting...\n\n"
                        f"[{progress_bar(percent)}] {percent:.1f}%\n"
                        f"🚀 {speed:.2f}x\n"
                        f"⏱ ETA: {int(eta)} sec"
                    )
                except:
                    pass

    await process.wait()

# 🎬 MAIN HANDLER
@bot.on_message(filters.video)
async def handler(client, message: Message):
    msg = await message.reply("🚀 Starting...")

    try:
        # 📥 DOWNLOAD
        start = time.time()
        file_path = await message.download(
            progress=lambda c, t: asyncio.create_task(
                tg_progress(c, t, msg, start, "📥 Downloading...")
            )
        )

        # ⏱ GET DURATION
        duration_cmd = f'ffprobe -v error -show_entries format=duration -of csv=p=0 "{file_path}"'
        try:
            duration = float(subprocess.getoutput(duration_cmd))
        except:
            duration = 0

        await msg.edit("🔄 Starting Conversion...")

        output = file_path.rsplit(".", 1)[0] + "_converted.mp4"

        # ⚙️ CONVERT
        await convert_video(file_path, output, duration, msg)

        # 📤 SAFE UPLOAD (FIXED)
        if not os.path.exists(output):
            await msg.edit("❌ Output file not found!")
            return

        size = os.path.getsize(output) / (1024 * 1024)
        await msg.edit(f"📤 Uploading...\n📦 Size: {size:.2f} MB")

        start = time.time()
        try:
            sent = await message.reply_video(
                video=output,
                supports_streaming=True,
                progress=lambda c, t: asyncio.create_task(
                    tg_progress(c, t, msg, start, "📤 Uploading...")
                )
            )
        except Exception as e:
            await msg.edit(f"❌ Upload Error:\n{str(e)}")
            return

        if not sent:
            await msg.edit("❌ Upload failed!")
            return

        # 🗑 DELETE AFTER SUCCESS
        await asyncio.sleep(1)

        try:
            await sent.delete()
        except:
            pass

        # 🧹 CLEAN FILES
        if os.path.exists(file_path):
            os.remove(file_path)
        if os.path.exists(output):
            os.remove(output)

        await msg.edit("✅ Done ⚡\n🗑 Auto Cleaned")

    except Exception as e:
        await msg.edit(f"❌ Error:\n{str(e)}")

# 🟢 START COMMAND
@bot.on_message(filters.command("start"))
async def start(client, message: Message):
    await message.reply_text(
        "👋 Hello!\n\n"
        "🎬 Send video\n"
        "⚡ H.265 → H.264 Ultra Fast\n"
        "📊 Full Progress (Download + Convert + Upload)\n"
        "🗑 Auto Delete Enabled"
    )

bot.run()
