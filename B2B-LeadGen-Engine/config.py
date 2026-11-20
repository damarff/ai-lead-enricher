import os

# Telegram Bot Credentials
# Replace with actual bot token and chat ID before running in production
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN_HERE")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "YOUR_TELEGRAM_CHAT_ID_HERE")

# Upwork Search Targeting (Niche: B2B / Web Development / Automation)
TARGET_URLS = [
    "https://www.upwork.com/nx/search/jobs/?q=webflow&sort=recency",
    "https://www.upwork.com/nx/search/jobs/?q=automation%20expert&sort=recency"
]

# Filtering Criteria
MINIMUM_BUDGET = 500  # Will be used by the Lysta AI agent later, or simple parsing

# Engine Settings
SLEEP_INTERVAL_SECONDS = 300  # Poll every 5 minutes
