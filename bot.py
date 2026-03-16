import os
import time
import subprocess
import requests
from pyrogram import Client, filters

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CATBOX_HASH = os.environ.get("CATBOX_HASH")

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
            f"⚡ {speed:.2f} MB/s\n"
            f"📦 {done:.2f}/{total_mb:.2f} MB"
        )


@app.on_message(filters.command("start"))
async def start(_, message):

    await message.reply_text(
        "🎬 MKV → MP4 BOT\n\n"
        "Send MKV video under 500MB\n"
        "Converted file will be uploaded to Catbox."
    )


def upload_catbox(file):

    url = "https://catbox.moe/user/api.php"

    data = {
        "reqtype": "fileupload",
        "userhash": CATBOX_HASH
    }

    files = {
        "fileToUpload": open(file, "rb")
    }

    r = requests.post(url, data=data, files=files)

    return r.text


@app.on_message(filters.video)
async def convert(client, message):

    size = message.video.file_size

    if size > 500 * 1024 * 1024:
        return await message.reply("❌ File must be under 500MB")

    status = await message.reply("📥 Downloading...")

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

    process = subprocess.run(cmd)

    if process.returncode != 0:
        await status.edit("❌ Remux failed")
        return

    await status.edit("☁ Uploading to Catbox...")

    link = upload_catbox(output)

    await message.reply_text(
        f"✅ Upload Complete\n\n🔗 {link}"
    )

    os.remove(file_path)
    os.remove(output)

    await status.delete()


if __name__ == "__main__":
    print("Bot Starting...")
    app.run()
