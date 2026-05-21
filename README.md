# AI Lead Enricher

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![MIT License](https://img.shields.io/badge/license-MIT-green)

**Enrich raw B2B leads with AI — company websites → structured data.**

Given a CSV of company names, this tool scrapes the web (via polite requests with
rotating user-agents) and feeds the raw content to an LLM (OpenAI-compatible API)
that extracts structured business intelligence: industry, company size, tech stack,
key people, and recent developments.

---

## How It Works

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│ companies   │────▶│ Web Scraper      │────▶│ LLM Enricher        │
│ .csv        │     │ (DuckDuckGo +    │     │ (OpenAI-compatible  │
│             │     │  direct website +│     │  API)               │
│             │     │  LinkedIn)       │     │                     │
└─────────────┘     └──────────────────┘     └──────────┬──────────┘
                                                         │
                                                         ▼
                                                  ┌──────────────┐
                                                  │ Enriched     │
                                                  │ .csv         │
                                                  └──────────────┘
```

---

## Features

- **Multi-source scraping** — searches DuckDuckGo, guesses the company website,
  and attempts LinkedIn company pages for maximum coverage.
- **LLM-powered extraction** — uses any OpenAI-compatible API (GPT-4o, Claude,
  local models) to extract structured data from unstructured web text.
- **Polite & resilient** — 1–2 s delays between requests, rotating User-Agent
  headers, 15 s timeouts, and graceful fallback if a source fails.
- **Headless mode** — `--headless` flag skips web scraping for testing or
  dry-runs.
- **Configurable** — all LLM and scraping settings live in a single `config.yaml`.
- **Portfolio-grade output** — enriched CSV with industry, size, tech stack,
  key people, recent developments, and confidence scores.

---

## Quick Start

1. **Clone the repo** (or copy the files to your project):

   ```bash
   git clone https://github.com/your-org/ai-lead-enricher.git
   cd ai-lead-enricher
   ```

2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Set your LLM API key:**

   ```bash
   export LLM_API_KEY="sk-your-openai-key"
   ```

   Or edit `config.yaml` and set `api_key` directly (not recommended for shared
   environments).

4. **Run the enrichment:**

   ```bash
   python main.py sample_data/companies.csv --output enriched.csv
   ```

5. **Run tests:**

   ```bash
   python test.py
   ```

---

## Sample Output

| company_name | industry      | size_estimate | tech_stack                   | key_people                        | recent_developments                | confidence_score |
|-------------|---------------|---------------|------------------------------|-----------------------------------|------------------------------------|------------------|
| Notion      | Productivity  | 501-1000      | ["React","TypeScript","AWS"] | [{"name":"Ivan Zhao","title":"CEO"}] | ["Launched AI features","Hiring"] | 85               |
| Vercel      | Cloud/DevTools| 201-500       | ["Next.js","React","Edge"]   | [{"name":"Guillermo Rauch","title":"CEO"}] | ["$150M Series D","Next.js Conf"] | 90               |

*Actual output depends on the LLM model and the scraped web content.*

---

## Tech Stack

| Component     | Technology                        |
|---------------|-----------------------------------|
| Language      | Python 3.10+                      |
| HTTP / Scraping | `requests`, `BeautifulSoup 4`, `fake-useragent` |
| Parsing       | `lxml`                            |
| LLM API       | OpenAI-compatible (GPT-4o, Claude, local) |
| Configuration | `PyYAML`                          |

---

## Use Cases

- **B2B Sales Prospecting** — quickly enrich a list of target accounts with
  technographic and firmographic data.
- **Market Research** — gather intelligence on competitors (tech stack, hiring
  trends, funding).
- **Recruitment Sourcing** — identify key people and recent hiring signals at
  target companies.
- **Investor Analysis** — track recent developments (funding, product launches)
  across a portfolio.

---

## Project Structure

```
ai-lead-enricher/
├── __init__.py          # Package marker
├── main.py              # CLI entry point (argparse)
├── scraper.py           # Multi-source web scraper
├── enricher.py          # LLM enrichment module
├── config.yaml          # LLM & scraping configuration
├── requirements.txt     # Python dependencies
├── test.py              # 6 test cases (unittest)
├── sample_data/
│   └── companies.csv    # 5 sample companies
└── README.md            # This file
```

---

## License

MIT

---

Built for [Hermes Agent](https://github.com/nousresearch/hermes-agent) — the
autonomous coding assistant by Nous Research.
