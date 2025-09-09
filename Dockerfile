FROM python:3.13-slim

WORKDIR /app

# Install curl, Node.js, and other dependencies needed for lash and opencode
RUN apt-get update && apt-get install -y \
    curl \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Install lash CLI tool
RUN curl -fsSL https://raw.githubusercontent.com/lacymorrow/lash/main/install | bash

# Install npx globally for opencode configuration
RUN npm install -g npx

# Add lash to PATH
ENV PATH="/root/.lash/bin:$PATH"

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "alpaca_mcp_server.py"]
