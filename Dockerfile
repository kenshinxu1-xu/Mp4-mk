FROM python:3.10-slim

RUN apt update && apt install -y ffmpeg

WORKDIR /app

COPY . .

RUN pip install pyrofork tgcrypto

CMD ["python", "bot.py"]
