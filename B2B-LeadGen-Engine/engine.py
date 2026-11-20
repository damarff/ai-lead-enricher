import time
import argparse
from DrissionPage import ChromiumPage, ChromiumOptions
import database
import notifier
from config import TARGET_URLS, SLEEP_INTERVAL_SECONDS

def setup_browser():
    co = ChromiumOptions()
    co.auto_port()
    # Ensure it runs silently/headless if on a server, but for local MVP keeping it default is fine
    # co.headless(True) 
    page = ChromiumPage(addr_or_opts=co)
    return page

def extract_jobs_from_page(page):
    """
    Extracts job cards from the Upwork search results page.
    """
    jobs = []
    print("[Engine] Waiting for job cards to render...")
    
    try:
        time.sleep(5) # Let the page load
        job_cards = page.eles('.job-tile')
    except Exception as e:
        print(f"[Engine] Could not find job cards. Error: {e}")
        return jobs

    for card in job_cards:
        try:
            # Extract basic info
            title_ele = card.ele('.job-tile-title')
            if not title_ele:
                continue
                
            # If the title element contains an 'a' tag, get its text and link, otherwise use title_ele
            link_ele = title_ele.ele('t:a')
            if link_ele:
                title = link_ele.text
                job_url = link_ele.link
            else:
                title = title_ele.text
                job_url = "https://upwork.com"

            # Extract ID from URL
            job_id = ""
            if "~" in job_url:
                job_id = job_url.split("~")[1].split("/")[0].split("?")[0]
            else:
                job_id = title.replace(" ", "")

            # For MVP, just get the full card text snippet for description
            card_text = card.text
            # Try to grab budget by looking for $ sign in the card text, or just say 'See Link'
            budget = "See Link"
            if "$" in card_text:
                budget_lines = [line for line in card_text.split('\n') if '$' in line]
                if budget_lines:
                    budget = budget_lines[0].strip()

            jobs.append({
                "id": job_id,
                "title": title,
                "url": job_url,
                "budget": budget,
                "description": card_text.replace('\n', ' ')[:250]
            })
        except Exception as e:
            print(f"[Engine] Error parsing a job card: {e}")
            continue

    return jobs

def run_extraction_loop(test_mode=False):
    print("🚀 Starting B2B Lead Generation Engine...")
    page = setup_browser()
    
    while True:
        for url in TARGET_URLS:
            print(f"\n[Engine] Fetching targets from: {url}")
            page.get(url)
            time.sleep(5) # Allow dynamic content to settle
            
            jobs = extract_jobs_from_page(page)
            print(f"[Engine] Found {len(jobs)} jobs on page.")
            
            for job in jobs:
                # Deduplication Check
                if not database.is_job_sent(job['id']):
                    print(f"  [+] New Lead Detected: {job['title']}")
                    # Send alert
                    success = notifier.send_telegram_alert(
                        job_title=job['title'],
                        job_url=job['url'],
                        budget=job['budget'],
                        description=job['description']
                    )
                    
                    if success:
                        database.mark_job_sent(
                            job_id=job['id'],
                            title=job['title'],
                            url=job['url'],
                            budget=job['budget'],
                            description=job['description']
                        )
                else:
                    # print(f"  [-] Skipping existing: {job['title']}")
                    pass
                    
        if test_mode:
            print("[Engine] Test mode active. Exiting after 1 iteration.")
            break
            
        print(f"\n[Engine] Sleeping for {SLEEP_INTERVAL_SECONDS} seconds...")
        time.sleep(SLEEP_INTERVAL_SECONDS)
        
    page.quit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the B2B Lead Gen Engine")
    parser.add_argument("--test-mode", action="store_true", help="Run only one iteration without sleeping")
    args = parser.parse_args()
    
    run_extraction_loop(test_mode=args.test_mode)
