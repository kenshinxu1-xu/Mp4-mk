import os
import time
import subprocess
from pyrogram import Client, filters

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

app = Client(
    "remuxbot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)


async def progress(current, total, message, start, text):

    now = time.time()
    diff = now - start

    if diff % 2 < 1:
        percent = current * 100 / total
        bar = "█" * int(percent / 5) + "░" * (20 - int(percent / 5))

        speed = current / diff / 1024 / 1024
        done = current / 1024 / 1024
        total_mb = total / 1024 / 1024

        await message.edit(
            f"{text}\n\n"
            f"[{bar}] {percent:.2f}%\n\n"
            f"⚡ Speed: {speed:.2f} MB/s\n"
            f"📦 {done:.2f}/{total_mb:.2f} MB"
        )


@app.on_message(filters.command("start"))
async def start(_, message):

    await message.reply_text(
        "🎬 **MKV → MP4 REMUX BOT**\n\n"
        "Send any **MKV video** and I will convert it to **MP4 instantly**.\n\n"
        "⚡ Max Size: 500MB\n"
        "⚡ No Quality Loss\n"
        "⚡ Fast Container Change\n"
        "⚡ Real Time Progress"
    )


@app.on_message(filters.video)
async def convert(client, message):

    size = message.video.file_size

    if size > 500 * 1024 * 1024:
        return await message.reply("❌ File must be under 500MB")

    status = await message.reply("📥 Starting Download...")

    start = time.time()

    file_path = await message.download(
        progress=progress,
        progress_args=(status, start, "📥 Downloading")
    )

    await status.edit("⚙️ Remuxing MKV → MP4...")

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
        caption="✅ MKV ➜ MP4 Completed",
        progress=progress,
        progress_args=(status, start, "📤 Uploading")
    )

    os.remove(file_path)
    os.remove(output)

    await status.delete()


app.run()
