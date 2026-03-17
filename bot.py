import os
import re
import time
import asyncio
import subprocess
from pyrogram import Client, filters
from pyrogram.types import Message

# 🔐 ENV VARIABLES (Railway me set karna)
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

bot = Client(
    "ultra_fast_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# 🟢 START COMMAND
@bot.on_message(filters.command("start"))
async def start(client, message: Message):
    await message.reply_text(
        "👋 Hello Bro!\n\n"
        "🎬 Send H.265 video\n"
        "⚡ I convert to H.264 (Ultra Fast)\n"
        "📊 Real-time Progress\n"
        "🗑 Auto delete after upload"
    )

# 🔍 GET CODEC
def get_codec(file):
    cmd = f'ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of csv=p=0 "{file}"'
    return subprocess.getoutput(cmd).strip()

# ⏱ GET DURATION
def get_duration(file):
    cmd = f'ffprobe -v error -show_entries format=duration -of csv=p=0 "{file}"'
    try:
        return float(subprocess.getoutput(cmd))
    except:
        return 0

# ⏳ TIME → SECONDS
def time_to_seconds(t):
    try:
        h, m, s = t.split(":")
        return float(h)*3600 + float(m)*60 + float(s)
    except:
        return 0

# ⚡ CONVERT WITH REAL PROGRESS
async def convert_video(input_file, output_file, duration, msg):
    cmd = [
        "ffmpeg",
        "-i", input_file,
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "28",
        "-c:a", "copy",
        "-progress", "pipe:1",   # 🔥 IMPORTANT
        "-nostats",
        output_file
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL
    )

    start_time = time.time()
    last_update = 0

    while True:
        line = await process.stdout.readline()
        if not line:
            break

        line = line.decode().strip()

        if "out_time=" in line:
            time_str = line.split("=")[1]

            current = time_to_seconds(time_str)
            percent = min((current / duration) * 100, 100)

            elapsed = time.time() - start_time
            speed = current / elapsed if elapsed > 0 else 0
            eta = (duration - current) / speed if speed > 0 else 0

            if time.time() - last_update > 2:
                last_update = time.time()

                filled = int(percent // 5)
                bar = "█" * filled + "░" * (20 - filled)

                try:
                    await msg.edit_text(
                        f"⚙️ Converting...\n\n"
                        f"[{bar}] {percent:.1f}%\n"
                        f"⏱ ETA: {int(eta)} sec\n"
                        f"🚀 Speed: {speed:.2f}x"
                    )
                except:
                    pass

    await process.wait()

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stderr=asyncio.subprocess.PIPE
    )

    start_time = time.time()
    last_update = 0

    while True:
        line = await process.stderr.readline()
        if not line:
            break

        line = line.decode(errors="ignore")

        if "time=" in line:
            match = re.search(r"time=(\d+:\d+:\d+\.\d+)", line)
            if match and duration > 0:
                current = time_to_seconds(match.group(1))
                percent = min((current / duration) * 100, 100)

                elapsed = time.time() - start_time
                speed = current / elapsed if elapsed > 0 else 0
                eta = (duration - current) / speed if speed > 0 else 0

                if time.time() - last_update > 2:
                    last_update = time.time()

                    filled = int(percent // 5)
                    bar = "█" * filled + "░" * (20 - filled)

                    text = (
                        f"⚙️ Converting...\n\n"
                        f"[{bar}] {percent:.1f}%\n"
                        f"⏱ ETA: {int(eta)} sec\n"
                        f"🚀 Speed: {speed:.2f}x"
                    )

                    try:
                        await msg.edit_text(text)
                    except:
                        pass

    await process.wait()

# 🎬 VIDEO HANDLER
@bot.on_message(filters.video)
async def handler(client, message: Message):
    msg = await message.reply("📥 Downloading...")

    try:
        # 📥 DOWNLOAD
        file_path = await message.download()

        # 🔍 CHECK CODEC
        codec = get_codec(file_path)

        # ✅ SKIP IF ALREADY H264
        if codec == "h264":
            await msg.edit("✅ Already H.264\n📤 Uploading...")
            sent = await message.reply_video(file_path)

            await asyncio.sleep(1)
            await sent.delete()
            os.remove(file_path)

            await msg.edit("🗑 Cleaned ⚡")
            return

        # ⏱ DURATION
        duration = get_duration(file_path)

        await msg.edit("🔄 Starting Conversion...")

        output = file_path.rsplit(".", 1)[0] + "_converted.mp4"

        # ⚡ CONVERT
        await convert_video(file_path, output, duration, msg)

        # 📤 UPLOAD
        await msg.edit("📤 Uploading...")

        sent = await message.reply_video(output)

        # 🗑 AUTO DELETE
        await asyncio.sleep(1)
        await sent.delete()

        # 🧹 CLEAN FILES
        if os.path.exists(file_path):
            os.remove(file_path)
        if os.path.exists(output):
            os.remove(output)

        await msg.edit("✅ Done ⚡\n🗑 Files Deleted")

    except Exception as e:
        await msg.edit(f"❌ Error:\n{str(e)}")

# 🚀 RUN BOT
bot.run(print("FFmpeg started"))
