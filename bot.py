import os
import time
import subprocess
from pyrogram import Client, filters

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

app = Client("remuxbot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


async def progress(current, total, message, start, text):

    now = time.time()
    diff = now - start

    if diff % 2 < 1:
        percent = current * 100 / total
        bar = "█" * int(percent / 5) + "░" * (20 - int(percent / 5))

        await message.edit(
            f"{text}\n\n"
            f"[{bar}] {percent:.2f}%"
        )


@app.on_message(filters.command("start"))
async def start(_, message):

    await message.reply(
        "⚡ **MKV → MP4 REMUX BOT**\n\n"
        "Send MKV video\n"
        "Max size: 500MB\n"
        "Files auto delete after upload"
    )


@app.on_message(filters.video)
async def convert(client, message):

    status = await message.reply("📥 Downloading...")

    file_path = None
    output = None

    try:

        start = time.time()

        file_path = await message.download(
            progress=progress,
            progress_args=(status, start, "📥 Downloading")
        )

        await status.edit("⚙️ Remuxing MKV → MP4...")

        output = file_path.rsplit(".", 1)[0] + ".mp4"

        cmd = [
            "ffmpeg",
            "-y",
            "-i", file_path,
            "-c:v", "copy",
            "-c:a", "copy",
            "-sn",
            output
        ]

        subprocess.run(cmd)

        start = time.time()

        await message.reply_video(
            output,
            caption="✅ MKV → MP4 Done",
            progress=progress,
            progress_args=(status, start, "📤 Uploading")
        )

        await status.delete()

    finally:

        # AUTO CLEANUP
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

        if output and os.path.exists(output):
            os.remove(output)
if __name__ == "__main__":
    print("Bot Starting...")
    app.run()
