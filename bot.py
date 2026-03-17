import os
import re
import time
import asyncio
import subprocess
from pyrogram import Client, filters
from pyrogram.types import Message
from config import *

bot = Client(
    "ultra_fast_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# 🔍 get codec
def get_codec(file):
    cmd = f'ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of csv=p=0 "{file}"'
    return subprocess.getoutput(cmd).strip()

# ⏱ get duration
def get_duration(file):
    cmd = f'ffprobe -v error -show_entries format=duration -of csv=p=0 "{file}"'
    return float(subprocess.getoutput(cmd))

# 🧮 convert time string to seconds
def time_to_seconds(time_str):
    h, m, s = time_str.split(":")
    return float(h)*3600 + float(m)*60 + float(s)

# ⚡ convert with REAL progress
async def convert_video(input_file, output_file, duration, msg):
    cmd = [
        "ffmpeg",
        "-i", input_file,
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "28",
        "-c:a", "copy",
        output_file
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stderr=asyncio.subprocess.PIPE
    )

    start = time.time()
    last_update = 0

    while True:
        line = await process.stderr.readline()
        if not line:
            break

        line = line.decode()

        if "time=" in line:
            match = re.search(r"time=(\d+:\d+:\d+\.\d+)", line)
            if match:
                current_time = time_to_seconds(match.group(1))
                percent = (current_time / duration) * 100

                elapsed = time.time() - start
                speed = current_time / elapsed if elapsed > 0 else 0
                eta = (duration - current_time) / speed if speed > 0 else 0

                # update every 2 sec
                if time.time() - last_update > 2:
                    last_update = time.time()

                    bar = "█" * int(percent // 5) + "░" * (20 - int(percent // 5))

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

# 🎬 handler
@bot.on_message(filters.video)
async def handler(client, message: Message):
    msg = await message.reply("📥 Downloading...")

    file_path = await message.download()

    codec = get_codec(file_path)

    if codec == "h264":
        await msg.edit("✅ Already H.264, Uploading...")
        sent = await message.reply_video(file_path)

        await asyncio.sleep(1)
        await sent.delete()
        os.remove(file_path)
        return

    duration = get_duration(file_path)

    await msg.edit("🔄 Starting Conversion...")

    output = file_path.rsplit(".", 1)[0] + "_converted.mp4"

    await convert_video(file_path, output, duration, msg)

    await msg.edit("📤 Uploading...")

    sent = await message.reply_video(output)

    await asyncio.sleep(1)
    await sent.delete()

    os.remove(file_path)
    os.remove(output)

    await msg.edit("✅ Done ⚡ (Auto Cleaned)")

bot.run()
