FROM python:3.9-slim

# System dependencies for ani-cli
RUN apt-get update && apt-get install -y \
    git curl grep sed coreutils \
    && rm -rf /var/lib/apt/lists/*

# Install ani-cli properly
RUN git clone https://github.com/pystardust/ani-cli.git /opt/ani-cli \
    && chmod +x /opt/ani-cli/ani-cli \
    && ln -s /opt/ani-cli/ani-cli /usr/local/bin/ani-cli

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

# Start the bot
CMD ["python", "main.py"]
