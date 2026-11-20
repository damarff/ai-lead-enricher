import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

def send_telegram_alert(job_title, job_url, budget, description):
    """
    Sends a formatted alert to the designated Telegram chat.
    """
    if TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        print("[Notifier] Telegram Token not configured. Simulating alert:")
        print(f"--- NEW LEAD ---\nTitle: {job_title}\nBudget: {budget}\nURL: {job_url}\n")
        return True

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    text = (
        f"🌟 *NEW HIGH-TICKET LEAD* 🌟\n\n"
        f"📌 *{job_title}*\n"
        f"💰 *Budget:* {budget}\n\n"
        f"📝 *Description snippet:*\n_{description[:200]}..._\n\n"
        f"🔗 [Apply Here]({job_url})"
    )
    
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print(f"[Notifier] Successfully sent alert for: {job_title}")
        return True
    except Exception as e:
        print(f"[Notifier] Failed to send Telegram alert: {e}")
        return False
