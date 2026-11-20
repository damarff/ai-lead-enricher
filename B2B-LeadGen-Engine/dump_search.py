from DrissionPage import ChromiumPage, ChromiumOptions

co = ChromiumOptions()
co.auto_port()
page = ChromiumPage(addr_or_opts=co)

print("Fetching URL...")
page.get("https://www.upwork.com/nx/search/jobs/?q=webflow&sort=recency", timeout=20)
print("Waiting 5 seconds...")
page.wait(5)
print("Dumping HTML...")
with open("search_dump.html", "w", encoding="utf-8") as f:
    f.write(page.html)
print("Done.")
page.quit()
