#!/usr/bin/env python3
"""Test suite for AI Lead Enricher.

All tests avoid real network calls — they mock or use local data.
Run with: python test.py
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

# Ensure the project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

import yaml

from enricher import _parse_llm_response, enrich_company
from main import _merge_enrichment, load_config, read_csv, write_csv
from scraper import _guess_website_url


class TestConfig(unittest.TestCase):
    """Test 1: Config loading returns correct defaults."""

    def test_load_config_defaults(self):
        """Load config.yaml and verify expected keys and default values."""
        config_path = PROJECT_ROOT / "config.yaml"
        self.assertTrue(config_path.exists(), "config.yaml must exist")

        config = load_config(str(config_path))
        self.assertIn("llm", config)
        self.assertIn("scraping", config)
        self.assertIn("output", config)

        llm = config["llm"]
        self.assertIn("endpoint", llm)
        self.assertIn("model", llm)
        self.assertIn("api_key", llm)
        self.assertIn("temperature", llm)
        # Check a sensible default
        self.assertGreaterEqual(llm["temperature"], 0)

        scraping = config["scraping"]
        self.assertIn("delay_between_requests", scraping)
        self.assertIn("timeout", scraping)
        self.assertGreater(scraping["timeout"], 0)

    def test_load_config_not_found(self):
        """Loading a nonexistent config raises FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            load_config("/nonexistent/config.yaml")


class TestCSV(unittest.TestCase):
    """Test 2: CSV parsing returns correct number of rows."""

    def setUp(self):
        self.sample_csv = PROJECT_ROOT / "sample_data" / "companies.csv"
        self.assertTrue(self.sample_csv.exists(), "sample CSV must exist")

    def test_parse_sample_csv(self):
        """Parsing sample_data/companies.csv returns 5 rows."""
        rows = read_csv(str(self.sample_csv))
        self.assertEqual(len(rows), 5)
        for row in rows:
            self.assertIn("company_name", row)
            self.assertIn("industry", row)

    def test_read_csv_empty(self):
        """Reading an empty CSV raises ValueError."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as f:
            f.write("company_name\n")
            tmp_path = f.name
        try:
            with self.assertRaises(ValueError):
                read_csv(tmp_path)
        finally:
            os.unlink(tmp_path)

    def test_read_csv_missing_column(self):
        """CSV without company_name column raises ValueError."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as f:
            f.write("foo,bar\n1,2\n")
            tmp_path = f.name
        try:
            with self.assertRaises(ValueError):
                read_csv(tmp_path)
        finally:
            os.unlink(tmp_path)

    def test_read_csv_not_found(self):
        """Reading a nonexistent CSV raises FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            read_csv("/tmp/nonexistent_xyz.csv")


class TestWebsiteGuess(unittest.TestCase):
    """Test 3: Website URL guessing from company names."""

    def test_simple_name(self):
        """Simple names become domain.com."""
        self.assertEqual(
            _guess_website_url("Notion"), "https://notion.com"
        )

    def test_name_with_spaces(self):
        """Spaces are removed."""
        self.assertEqual(
            _guess_website_url("Acme Corp"), "https://acmecorp.com"
        )

    def test_name_with_dots(self):
        """Dots are removed."""
        self.assertEqual(
            _guess_website_url("Fly.io"), "https://flyio.com"
        )

    def test_mixed_case(self):
        """Names are lowercased."""
        self.assertEqual(
            _guess_website_url("Vercel"), "https://vercel.com"
        )

    def test_multi_word(self):
        """Multi-word names without dots."""
        self.assertEqual(
            _guess_website_url("Linear"), "https://linear.com"
        )


class TestScrapeTimeout(unittest.TestCase):
    """Test 4: Scrape function handles failures gracefully."""

    @patch("scraper.requests.get")
    def test_fetch_url_failure_returns_none(self, mock_get):
        """When requests.get raises, _fetch_url returns None."""
        from requests.exceptions import ConnectionError as ReqConnectionError

        mock_get.side_effect = ReqConnectionError("Connection refused")
        # We test via the scraper module's _fetch_url indirectly
        from scraper import _fetch_url

        result = _fetch_url("https://example.com", timeout=5)
        self.assertIsNone(result)

    @patch("scraper.requests.get")
    def test_fetch_url_timeout(self, mock_get):
        """A timeout exception is handled gracefully."""
        from requests.exceptions import Timeout

        mock_get.side_effect = Timeout("timed out")
        from scraper import _fetch_url

        result = _fetch_url("https://example.com", timeout=1)
        self.assertIsNone(result)

    @patch("scraper._fetch_url")
    def test_scrape_company_no_data(self, mock_fetch):
        """scrape_company returns empty strings when all sources fail."""
        mock_fetch.return_value = None
        config = {
            "delay_between_requests": 0,
            "max_sources_per_company": 3,
            "timeout": 5,
        }
        from scraper import scrape_company

        result = scrape_company("NonexistentCompanyXYZ", config)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["raw_text"], "")
        self.assertEqual(result["urls_found"], "")


class TestEnrichmentParsing(unittest.TestCase):
    """Test 5: LLM enrichment parses valid JSON correctly."""

    def test_parse_valid_json(self):
        """_parse_llm_response handles a complete valid JSON response."""
        response = json.dumps(
            {
                "industry": "Software Development",
                "size_estimate": "51-200",
                "tech_stack": ["Python", "React", "AWS"],
                "key_people": [
                    {"name": "Alice Smith", "title": "CEO"},
                    {"name": "Bob Jones", "title": "CTO"},
                ],
                "recent_developments": [
                    "Raised $10M Series A",
                    "Hired 20 new engineers",
                ],
                "confidence_score": 85,
            }
        )
        result = _parse_llm_response(response)
        self.assertEqual(result["industry"], "Software Development")
        self.assertEqual(result["size_estimate"], "51-200")
        self.assertEqual(len(result["tech_stack"]), 3)
        self.assertEqual(len(result["key_people"]), 2)
        self.assertEqual(len(result["recent_developments"]), 2)
        self.assertEqual(result["confidence_score"], 85)

    def test_parse_partial_json(self):
        """_parse_llm_response handles partial responses with nulls."""
        response = json.dumps(
            {
                "industry": "Fintech",
                "size_estimate": None,
                "tech_stack": [],
                "key_people": [],
                "recent_developments": [],
                "confidence_score": 40,
            }
        )
        result = _parse_llm_response(response)
        self.assertEqual(result["industry"], "Fintech")
        self.assertIsNone(result["size_estimate"])

    def test_parse_invalid_json_fallback(self):
        """_parse_llm_response falls back gracefully on bad input."""
        result = _parse_llm_response("this is not json at all")
        self.assertIn("_parse_error", result)
        self.assertEqual(result["confidence_score"], 0)

    def test_parse_json_in_code_block(self):
        """_parse_llm_response extracts JSON from markdown code blocks."""
        response = 'Here is the data:\n```json\n{"industry": "AI", "size_estimate": "11-50", "tech_stack": ["PyTorch"], "key_people": [], "recent_developments": [], "confidence_score": 70}\n```'
        result = _parse_llm_response(response)
        self.assertEqual(result["industry"], "AI")
        self.assertEqual(result["confidence_score"], 70)

    @patch("enricher.requests.post")
    def test_enrich_company_no_text(self, mock_post):
        """enrich_company returns default data when text is empty."""
        config = {
            "endpoint": "https://api.example.com/v1",
            "model": "gpt-4o-mini",
            "api_key": "test-key",
            "temperature": 0.1,
        }
        result = enrich_company("", config)
        self.assertEqual(result["confidence_score"], 0)
        self.assertIn("_note", result)

    @patch("enricher.requests.post")
    def test_enrich_company_api_error(self, mock_post):
        """enrich_company propagates API errors."""
        from requests.exceptions import HTTPError

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = HTTPError("401 Unauthorized")
        mock_post.return_value = mock_response

        config = {
            "endpoint": "https://api.example.com/v1",
            "model": "gpt-4o-mini",
            "api_key": "bad-key",
            "temperature": 0.1,
        }
        with self.assertRaises(Exception):
            enrich_company("Some text about a company.", config)


class TestMergeEnrichment(unittest.TestCase):
    """Test merge function combines row + enrichment correctly."""

    def test_merge_basic(self):
        """_merge_enrichment produces expected output dict."""
        row = {"company_name": "TestCorp", "notes": "interesting"}
        enrichment = {
            "industry": "Tech",
            "size_estimate": "11-50",
            "tech_stack": ["Python"],
            "key_people": [{"name": "Jane", "title": "CEO"}],
            "recent_developments": ["Launched product"],
            "confidence_score": 80,
        }
        merged = _merge_enrichment(row, enrichment, "https://testcorp.com")
        self.assertEqual(merged["company_name"], "TestCorp")
        self.assertEqual(merged["industry"], "Tech")
        self.assertIn("Python", merged["tech_stack"])
        self.assertIn("Jane", merged["key_people"])
        self.assertEqual(merged["confidence_score"], 80)
        self.assertEqual(merged["urls_found"], "https://testcorp.com")
        # Custom column preserved
        self.assertEqual(merged["notes"], "interesting")


class TestEndToEnd(unittest.TestCase):
    """Test 6: Full pipeline runs end-to-end with --headless flag."""

    @patch("enricher.requests.post")
    def test_headless_pipeline(self, mock_post):
        """Running main with --headless produces output CSV without real scraping."""
        # Mock LLM API response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "industry": "Software",
                                "size_estimate": "51-200",
                                "tech_stack": ["Python", "React"],
                                "key_people": [
                                    {"name": "Founder", "title": "CEO"}
                                ],
                                "recent_developments": ["Hiring"],
                                "confidence_score": 75,
                            }
                        )
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        # Create a temp input CSV
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as f:
            f.write("company_name,notes\nNotion,test\nVercel,test\n")
            input_path = f.name

        output_path = tempfile.mktemp(suffix=".csv")

        try:
            # Run the CLI
            from main import main as cli_main

            # Set LLM_API_KEY so the API key resolver doesn't fail
            old_key = os.environ.get("LLM_API_KEY")
            os.environ["LLM_API_KEY"] = "test-key-for-test"

            test_args = [
                "main.py",
                input_path,
                "--output",
                output_path,
                "--headless",
                "--config",
                str(PROJECT_ROOT / "config.yaml"),
            ]
            with patch.object(sys, "argv", test_args):
                cli_main()

            # Restore env
            if old_key is None:
                del os.environ["LLM_API_KEY"]
            else:
                os.environ["LLM_API_KEY"] = old_key

            # Verify output
            self.assertTrue(os.path.exists(output_path))
            with open(output_path, "r") as f:
                content = f.read()
            self.assertIn("Notion", content)
            self.assertIn("Vercel", content)
            self.assertIn("industry", content)
            self.assertIn("confidence_score", content)
        finally:
            os.unlink(input_path)
            if os.path.exists(output_path):
                os.unlink(output_path)


class TestWriteCSV(unittest.TestCase):
    """Test CSV writing utilities."""

    def test_write_csv_basic(self):
        """write_csv produces valid CSV with expected headers."""
        rows = [
            {
                "company_name": "A",
                "industry": "Tech",
                "size_estimate": "1-10",
                "tech_stack": '["Python"]',
                "key_people": '[]',
                "recent_developments": '[]',
                "confidence_score": 50,
                "urls_found": "",
            }
        ]
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as f:
            tmp_path = f.name
        try:
            write_csv(rows, tmp_path, include_raw_text=False)
            with open(tmp_path, "r") as f:
                content = f.read()
            self.assertIn("company_name", content)
            self.assertIn("industry", content)
            self.assertIn("tech_stack", content)
        finally:
            os.unlink(tmp_path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
