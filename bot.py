import os
import time
import asyncio
import subprocess
from pyrogram import Client, filters

API_ID = 123456
API_HASH = "YOUR_API_HASH"
BOT_TOKEN = "YOUR_BOT_TOKEN"

app = Client("remuxbot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


async def progress(current, total, message, start, text):

    now = time.time()
    diff = now - start

    if round(diff % 2) == 0:
        percent = current * 100 / total
        bar = "█" * int(percent / 5) + "░" * (20 - int(percent / 5))

        await message.edit(
            f"{text}\n\n"
            f"[{bar}] {percent:.2f}%\n"
            f"{current//1024//1024}MB / {total//1024//1024}MB"
        )


@app.on_message(filters.video)
async def remux(client, message):

    file_size = message.video.file_size

    if file_size > 500 * 1024 * 1024:
        return await message.reply("❌ Max file size 500MB")

    msg = await message.reply("📥 Starting download...")

    start = time.time()

    file_path = await message.download(
        progress=progress,
        progress_args=(msg, start, "📥 Downloading")
    )

    await msg.edit("⚡ Remuxing MKV → MP4...")

    output = file_path.rsplit(".", 1)[0] + ".mp4"

    cmd = [
        "ffmpeg",
        "-i",
        file_path,
        "-c",
        "copy",
        output
    ]

    subprocess.run(cmd)

    start = time.time()

    await message.reply_video(
        output,
        caption="✅ MKV → MP4 Remux Complete",
        progress=progress,
        progress_args=(msg, start, "📤 Uploading MP4")
    )

    os.remove(file_path)
    os.remove(output)

    await msg.delete()


app.run()
