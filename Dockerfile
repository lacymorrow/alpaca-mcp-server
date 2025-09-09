FROM python:3.13-slim

WORKDIR /app

# Install curl, Node.js, and other dependencies needed for lash and opencode
RUN apt-get update && apt-get install -y \
    bash \
    curl \
    jq \
    nodejs \
    npm \
    util-linux \
    && rm -rf /var/lib/apt/lists/*

# Install lash CLI tool
RUN curl -fsSL https://raw.githubusercontent.com/lacymorrow/lash/main/install | bash

# Install npx globally for opencode configuration
RUN npm install -g npx

# Add lash to PATH
ENV PATH="/root/.lash/bin:$PATH"

COPY . .

# Install scheduled tick script
RUN install -m 0755 scripts/alpaca-bot-tick.sh /usr/local/bin/alpaca-bot-tick.sh

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "alpaca_mcp_server.py"]
