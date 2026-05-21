"""Company website scraper module.

Attempts to gather raw text content about a company from multiple sources:
  1. DuckDuckGo search for "{company_name} about" and "{company_name} careers"
  2. Direct website guess: company_name.lower().replace(' ','') + '.com'
  3. LinkedIn public company profile (via requests)

All requests use fake User-Agent headers and polite delays.
"""

import logging
import re
import time
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

logger = logging.getLogger(__name__)

ua = UserAgent()


def _get_headers() -> Dict[str, str]:
    """Generate request headers with a random User-Agent."""
    return {
        "User-Agent": ua.random,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }


def _fetch_url(url: str, timeout: int = 15) -> Optional[str]:
    """Fetch a URL and return the raw HTML text.

    Args:
        url: The URL to fetch.
        timeout: Request timeout in seconds.

    Returns:
        The response text on success, or None on failure.
    """
    try:
        resp = requests.get(url, headers=_get_headers(), timeout=timeout)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as exc:
        logger.debug("Failed to fetch %s: %s", url, exc)
        return None


def _extract_text(html: str, max_length: int = 10_000) -> str:
    """Extract readable text from HTML, stripping scripts and styles.

    Args:
        html: Raw HTML content.
        max_length: Maximum characters to return.

    Returns:
        Cleaned text content, truncated to max_length.
    """
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = (line.strip() for line in text.splitlines())
    text = "\n".join(line for line in lines if line)
    return text[:max_length]


def _duckduckgo_search(query: str, timeout: int = 15) -> List[str]:
    """Search DuckDuckGo and return result page URLs.

    Args:
        query: The search query string.
        timeout: Request timeout in seconds.

    Returns:
        A list of result page URLs (up to 5).
    """
    urls: List[str] = []
    params = {"q": query}
    try:
        resp = requests.get(
            "https://html.duckduckgo.com/html/",
            params=params,
            headers=_get_headers(),
            timeout=timeout,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        for a_tag in soup.select("a.result__a"):
            href = a_tag.get("href", "")
            if href.startswith("http"):
                urls.append(href)
            elif href.startswith("//"):
                urls.append("https:" + href)
    except requests.RequestException as exc:
        logger.debug("DuckDuckGo search failed for '%s': %s", query, exc)
    return urls[:5]


def _scrape_duckduckgo(company_name: str, config: Dict) -> Optional[str]:
    """Search DuckDuckGo for company info and scrape found pages.

    Args:
        company_name: The company name to search for.
        config: Scraping configuration dict.

    Returns:
        Combined text content from found pages, or None.
    """
    delay = config.get("delay_between_requests", 1.5)
    timeout = config.get("timeout", 15)
    combined: List[str] = []

    queries = [f"{company_name} about", f"{company_name} careers"]
    seen_urls: set = set()

    for query in queries:
        urls = _duckduckgo_search(query, timeout=timeout)
        for url in urls:
            if url in seen_urls:
                continue
            seen_urls.add(url)
            time.sleep(delay)
            html = _fetch_url(url, timeout=timeout)
            if html:
                text = _extract_text(html)
                combined.append(f"--- Source: {url} ---\n{text}")
                logger.info("Scraped DuckDuckGo result: %s", url)
        time.sleep(delay)

    return "\n\n".join(combined) if combined else None


def _guess_website_url(company_name: str) -> str:
    """Guess the company website URL from its name.

    Args:
        company_name: The company name.

    Returns:
        A guessed URL string.
    """
    domain = company_name.lower().replace(" ", "").replace(".", "")
    # Handle common TLDs — default to .com
    return f"https://{domain}.com"


def _scrape_direct_website(company_name: str, config: Dict) -> Optional[str]:
    """Guess and scrape the company's direct website.

    Args:
        company_name: The company name.
        config: Scraping configuration dict.

    Returns:
        Extracted text from the website, or None.
    """
    timeout = config.get("timeout", 15)
    url = _guess_website_url(company_name)
    logger.info("Attempting direct website: %s", url)
    html = _fetch_url(url, timeout=timeout)
    if html:
        return _extract_text(html)
    return None


def _scrape_linkedin(company_name: str, config: Dict) -> Optional[str]:
    """Attempt to scrape a public LinkedIn company page.

    Args:
        company_name: The company name.
        config: Scraping configuration dict.

    Returns:
        Extracted text from LinkedIn, or None.
    """
    timeout = config.get("timeout", 15)
    slug = company_name.lower().replace(" ", "-").replace(".", "")
    url = f"https://www.linkedin.com/company/{slug}/about/"
    logger.info("Attempting LinkedIn: %s", url)
    html = _fetch_url(url, timeout=timeout)
    if html:
        return _extract_text(html)
    return None


def scrape_company(company_name: str, config: Dict) -> Dict[str, str]:
    """Scrape web content about a company from multiple sources.

    Tries up to max_sources_per_company sources in order:
      1. DuckDuckGo search + scrape of result pages
      2. Direct website guess
      3. LinkedIn company page

    Args:
        company_name: Name of the company to research.
        config: Scraping configuration dictionary (from config.yaml).

    Returns:
        A dict with keys:
          - 'raw_text': combined scraped text content (or empty string)
          - 'urls_found': newline-separated URLs discovered (or empty string)
    """
    max_sources = config.get("max_sources_per_company", 3)
    delay = config.get("delay_between_requests", 1.5)

    result: Dict[str, str] = {"raw_text": "", "urls_found": ""}
    all_text: List[str] = []
    all_urls: List[str] = []
    sources_tried = 0

    # Source 1: DuckDuckGo
    if sources_tried < max_sources:
        logger.info("Source 1: DuckDuckGo search for %s", company_name)
        text = _scrape_duckduckgo(company_name, config)
        if text:
            all_text.append(text)
            sources_tried += 1
        time.sleep(delay)

    # Source 2: Direct website
    if sources_tried < max_sources:
        logger.info("Source 2: Direct website for %s", company_name)
        text = _scrape_direct_website(company_name, config)
        if text:
            guessed_url = _guess_website_url(company_name)
            all_text.append(f"--- Source: {guessed_url} ---\n{text}")
            all_urls.append(guessed_url)
            sources_tried += 1
        time.sleep(delay)

    # Source 3: LinkedIn
    if sources_tried < max_sources:
        logger.info("Source 3: LinkedIn for %s", company_name)
        text = _scrape_linkedin(company_name, config)
        if text:
            slug = company_name.lower().replace(" ", "-").replace(".", "")
            linkedin_url = f"https://www.linkedin.com/company/{slug}/about/"
            all_text.append(f"--- Source: {linkedin_url} ---\n{text}")
            all_urls.append(linkedin_url)
            sources_tried += 1

    result["raw_text"] = "\n\n".join(all_text)
    result["urls_found"] = "\n".join(all_urls)
    return result
