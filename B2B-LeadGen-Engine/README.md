# B2B Lead Gen Engine

Automated lead generation engine using browser automation (DrissionPage). Searches target websites, extracts leads, stores in database, and sends notifications.

## Features

- **Browser automation** — DrissionPage (Chromium) with anti-detection
- **Multi-site scraping** — configurable target URLs
- **Database storage** — SQLite with deduplication
- **Notifications** — real-time alerts for new leads
- **API** — FastAPI endpoint for lead queries

## Tech Stack

- Python + DrissionPage (Chromium automation)
- FastAPI (REST API)
- SQLite (data storage)

## Quick Start

```bash
pip install -r requirements.txt
python engine.py
```
