#!/usr/bin/env python3
"""AI Lead Enricher — CLI entry point.

Reads a CSV of company names, scrapes their websites, and uses an LLM
to extract structured business data. Outputs an enriched CSV.
"""

import argparse
import csv
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from enricher import enrich_company
from scraper import scrape_company

logger = logging.getLogger(__name__)


def load_config(path: Optional[str] = None) -> Dict[str, Any]:
    """Load and return the YAML configuration.

    Args:
        path: Path to the config file. If None, searches common locations.

    Returns:
        A dict with 'llm', 'scraping', and 'output' sections.

    Raises:
        FileNotFoundError: If no config file is found.
    """
    search_paths: List[Path] = []
    if path:
        explicit = Path(path)
        if not explicit.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        search_paths.append(explicit)
    search_paths.extend([
        Path("config.yaml"),
        Path(__file__).parent / "config.yaml",
        Path.home() / ".hermes" / "hermes-agent" / "config.yaml",
    ])

    for sp in search_paths:
        if sp.exists():
            with open(sp, "r") as f:
                config: Dict[str, Any] = yaml.safe_load(f) or {}
                logger.info("Loaded config from %s", sp)
                return config

    raise FileNotFoundError(
        "Config file not found. Create config.yaml or pass --config."
    )


def read_csv(filepath: str) -> List[Dict[str, str]]:
    """Read a CSV file and return a list of row dicts.

    Args:
        filepath: Path to the CSV file.

    Returns:
        A list of dicts, one per row, with column names as keys.

    Raises:
        FileNotFoundError: If the CSV file does not exist.
        ValueError: If the CSV is empty or missing required columns.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Input CSV not found: {filepath}")

    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        raise ValueError(f"CSV file is empty: {filepath}")

    if "company_name" not in rows[0]:
        raise ValueError(
            f"CSV must have a 'company_name' column. Found: {list(rows[0].keys())}"
        )

    return rows


def write_csv(
    rows: List[Dict[str, Any]], output_path: str, include_raw_text: bool = False
) -> None:
    """Write enriched rows to a CSV file.

    Args:
        rows: List of enriched row dicts.
        output_path: Destination file path.
        include_raw_text: If True, include a raw_text column.
    """
    if not rows:
        logger.warning("No rows to write.")
        return

    fieldnames = [
        "company_name",
        "industry",
        "size_estimate",
        "tech_stack",
        "key_people",
        "recent_developments",
        "confidence_score",
        "urls_found",
    ]
    if include_raw_text:
        fieldnames.insert(1, "raw_text")

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    logger.info("Wrote enriched data (%d rows) to %s", len(rows), output_path)


def _serialize_value(val: Any) -> str:
    """Convert a field value to a string suitable for CSV output.

    Lists and dicts are JSON-serialized.

    Args:
        val: The value to serialize.

    Returns:
        A string representation.
    """
    if isinstance(val, str):
        return val
    if isinstance(val, list):
        import json

        return json.dumps(val, ensure_ascii=False)
    if isinstance(val, dict):
        import json

        return json.dumps(val, ensure_ascii=False)
    if val is None:
        return ""
    return str(val)


def _merge_enrichment(
    row: Dict[str, str], enrichment: Dict[str, Any], urls_found: str
) -> Dict[str, Any]:
    """Merge enrichment results back into the original row.

    Args:
        row: The original CSV row (company_name, etc.).
        enrichment: The structured data from the LLM.
        urls_found: URLs discovered during scraping.

    Returns:
        A flat dict suitable for CSV output.
    """
    merged: Dict[str, Any] = {
        "company_name": row.get("company_name", ""),
        "industry": enrichment.get("industry"),
        "size_estimate": enrichment.get("size_estimate"),
        "tech_stack": _serialize_value(enrichment.get("tech_stack", [])),
        "key_people": _serialize_value(enrichment.get("key_people", [])),
        "recent_developments": _serialize_value(
            enrichment.get("recent_developments", [])
        ),
        "confidence_score": enrichment.get("confidence_score", 0),
        "urls_found": urls_found,
        "raw_text": row.get("raw_text", ""),
    }
    # Carry over any original notes
    if "notes" in row:
        merged["notes"] = row["notes"]
    return merged


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="AI Lead Enricher — enrich B2B leads with web scraping and LLM analysis"
    )
    parser.add_argument(
        "input_csv",
        help="Path to input CSV file with a 'company_name' column",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="enriched.csv",
        help="Output CSV path (default: enriched.csv)",
    )
    parser.add_argument(
        "--config",
        "-c",
        default=None,
        help="Path to config.yaml (default: search common locations)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Skip real web scraping (use for testing or if no browser access needed)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable DEBUG-level logging",
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Load config
    config = load_config(args.config)
    llm_config = config.get("llm", {})
    scraping_config = config.get("scraping", {})
    output_config = config.get("output", {})
    include_raw_text = output_config.get("include_raw_text", False)

    # Read input
    logger.info("Reading input CSV: %s", args.input_csv)
    rows = read_csv(args.input_csv)
    logger.info("Loaded %d companies", len(rows))

    # Process each company
    enriched_rows: List[Dict[str, Any]] = []
    for i, row in enumerate(rows):
        company_name = row.get("company_name", "").strip()
        if not company_name:
            logger.warning("Row %d has empty company_name, skipping", i)
            continue

        logger.info("Processing [%d/%d]: %s", i + 1, len(rows), company_name)

        if args.headless:
            # Skip scraping, use placeholder
            scraped = {
                "raw_text": f"[headless mode] No scraping performed for {company_name}",
                "urls_found": "",
            }
            enrichment = enrich_company(scraped["raw_text"], llm_config)
        else:
            # Scrape the web
            scraped = scrape_company(company_name, scraping_config)
            if not scraped["raw_text"]:
                logger.warning(
                    "No content scraped for %s, using placeholder", company_name
                )
                enrichment = enrich_company(
                    f"[no data found] {company_name}", llm_config
                )
            else:
                enrichment = enrich_company(scraped["raw_text"], llm_config)

        enriched_row = _merge_enrichment(
            row, enrichment, scraped.get("urls_found", "")
        )

        if include_raw_text:
            enriched_row["raw_text"] = scraped.get("raw_text", "")

        enriched_rows.append(enriched_row)

    # Write output
    write_csv(enriched_rows, args.output, include_raw_text)
    logger.info("Done. Enriched %d companies → %s", len(enriched_rows), args.output)


if __name__ == "__main__":
    main()
