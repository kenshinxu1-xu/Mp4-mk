import os
import time
import math
import asyncio
import subprocess
from pyrogram import Client, filters
from pyrogram.types import Message

# Railway environment variables se credentials uthayenge
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

app = Client("h265_converter_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Progress Bar Helper Function (To avoid Telegram flood limits, updates every 3 seconds)
async def progress_for_pyrogram(current, total, ud_type, message, start):
    now = time.time()
    diff = now - start
    if round(diff % 3.00) == 0 or current == total:
        percentage = current * 100 / total
        speed = current / diff if diff > 0 else 0
        elapsed_time = round(diff) * 1000
        time_to_completion = round((total - current) / speed) * 1000 if speed > 0 else 0
        estimated_total_time = elapsed_time + time_to_completion

        progress_str = "[{0}{1}]\nPercent: {2}%\n".format(
            ''.join(["█" for i in range(math.floor(percentage / 5))]),
            ''.join(["░" for i in range(20 - math.floor(percentage / 5))]),
            round(percentage, 2))
        
        tmp = progress_str + "{0} of {1}\nSpeed: {2}/s\nETA: {3}s".format(
            humanbytes(current), humanbytes(total), humanbytes(speed), round(time_to_completion / 1000))
        
        try:
            await message.edit(text=f"{ud_type}\n{tmp}")
        except Exception:
            pass # Ignore floodwaits or message not modified errors

def humanbytes(size):
    if not size: return "0 B"
    power = 2**10
    n = 0
    Dic_powerN = {0: ' ', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power
        n += 1
    return str(round(size, 2)) + " " + Dic_powerN[n] + 'B'

# Check if video is H.265 (HEVC)
def is_h265(file_path):
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=codec_name", "-of",
        "default=noprint_wrappers=1:nokey=1", file_path
    ]
    try:
        output = subprocess.check_output(cmd).decode().strip()
        return output.lower() == "hevc"
    except Exception as e:
        print(f"Error checking codec: {e}")
        return False
@app.on_message(filters.command("start"))
async def start_handler(client: Client, message: Message):
    await message.reply_text(
        "<blockquote>Bhai bot ekdum zinda hai!</blockquote> 🚀\n\n"
        "Mujhe koi bhi H.265 (HEVC) video ya document bhej, aur main usko superfast speed se H.264 mein convert kar dunga. 😎\n"
        "Bhej jaldi apni video!"
    )

@app.on_message(filters.video | filters.document)
async def handle_video(client: Client, message: Message):
    if not message.video and not message.document.mime_type.startswith('video/'):
        return

    msg = await message.reply("⏳ Downloading video...", quote=True)
    start_time = time.time()
    
    # 1. Download Video
    input_file = await message.download(
        progress=progress_for_pyrogram,
        progress_args=("⬇️ Downloading...", msg, start_time)
    )

    if not input_file:
        await msg.edit("❌ Download failed.")
        return

    await msg.edit("🔍 Checking video format...")

    # 2. Check Format
    if not is_h265(input_file):
        await msg.edit("✅ Ye video pehle se hi H.264 ya dusre format me hai. No need to convert!")
        await asyncio.sleep(2) # Wait a bit before deleting message
        await msg.delete()
        os.remove(input_file)
        return

    # 3. Convert Video (Fast preset)
    output_file = f"{input_file}_converted.mp4"
    await msg.edit("⚙️ H.265 detected! Converting to H.264 (Ultrafast mode). Please wait...")
    
    convert_cmd = [
        "ffmpeg", "-y", "-i", input_file, 
        "-c:v", "libx264", "-preset", "ultrafast", # Ultrafast for maximum speed
        "-crf", "28", # Decent quality with lower file size
        "-c:a", "copy", # Copy audio as is, saves time
        output_file
    ]

    # Run FFmpeg asynchronously so bot doesn't freeze
    process = await asyncio.create_subprocess_exec(
        *convert_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    await process.communicate()

    if not os.path.exists(output_file):
        await msg.edit("❌ Conversion failed.")
        os.remove(input_file)
        return

    # 4. Upload Converted Video
    start_time = time.time()
    await msg.edit("⬆️ Uploading converted video...")
    
    await message.reply_video(
        video=output_file,
        caption="✅ Converted from H.265 to H.264",
        progress=progress_for_pyrogram,
        progress_args=("⬆️ Uploading...", msg, start_time)
    )

    await msg.delete()

    # 5. Delete from server after 1 second
    await asyncio.sleep(1)
    if os.path.exists(input_file):
        os.remove(input_file)
    if os.path.exists(output_file):
        os.remove(output_file)
    print("🗑️ Cleaned up files from database/storage.")

if __name__ == "__main__":
    print("🤖 Bot is starting...")
    app.run()
