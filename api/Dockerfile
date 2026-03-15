FROM python:3.10-slim

# Install system dependencies including Google Chrome for Selenium
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Add Google Chrome Repository and install (Modern GPG Keyring approach)
RUN mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /etc/apt/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt
RUN pip install webdriver-manager uvicorn passlib bcrypt python-jose python-multipart

# Copy entirely API structure + scraper logic
COPY . .
WORKDIR /app/api

EXPOSE 8000

# Start Uvicorn Server using script
CMD ["bash", "start.sh"]
