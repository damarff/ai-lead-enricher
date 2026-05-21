"""LLM enrichment module.

Takes raw scraped text about a company and sends it to an LLM API
(OpenAI-compatible) to extract structured business data.
"""

import json
import logging
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert business researcher. Extract structured information about the company from the provided web scrapings.

Return your response as valid JSON with these fields:
- industry: str — the primary industry/sector the company operates in
- size_estimate: str — estimated company size (e.g., "1-10", "11-50", "51-200", "201-1000", "1000+")
- tech_stack: list[str] — technologies, frameworks, platforms mentioned (e.g., ["Python", "React", "AWS"])
- key_people: list[dict] — each with "name" and "title" keys for executives/founders mentioned
- recent_developments: list[str] — notable recent events like funding rounds, product launches, hiring sprees
- confidence_score: int — how confident you are in the extraction, 0-100

If you cannot find information for a field, use null or an empty list. Do NOT make up information that is not in the provided text. Return ONLY the JSON object, no markdown or commentary."""


def _resolve_api_key(llm_config: Dict[str, Any]) -> str:
    """Resolve the API key from config, expanding ${ENV_VAR} patterns.

    Args:
        llm_config: The LLM configuration dictionary.

    Returns:
        The resolved API key string.

    Raises:
        ValueError: If no API key can be resolved.
    """
    raw_key = llm_config.get("api_key", "")
    if not raw_key:
        raise ValueError("No api_key configured in llm section of config.yaml")

    # Expand ${ENV_VAR} pattern
    import os
    import re as _re

    match = _re.match(r"\$\{(\w+)\}", raw_key)
    if match:
        env_var = match.group(1)
        resolved = os.environ.get(env_var)
        if resolved:
            return resolved
        raise ValueError(
            f"Environment variable {env_var} is not set "
            f"(referenced in config.yaml llm.api_key)"
        )
    return raw_key


def _build_payload(
    text: str, model: str, temperature: float
) -> Dict[str, Any]:
    """Build the request payload for the LLM API.

    Args:
        text: The scraped text to analyze.
        model: The model name to use.
        temperature: The LLM temperature setting.

    Returns:
        A dict suitable for the OpenAI chat completions API.
    """
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Here is the scraped web content about a company:\n\n"
                    f"{text}\n\n"
                    f"Extract the requested structured data as JSON."
                ),
            },
        ],
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }


def _parse_llm_response(response_text: str) -> Dict[str, Any]:
    """Parse the LLM response text into a structured dict.

    Attempts JSON parsing with fallback for partial extraction.

    Args:
        response_text: The raw response string from the LLM.

    Returns:
        A dict with enrichment fields, using defaults for missing keys.
    """
    # Try direct JSON parse
    try:
        data = json.loads(response_text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    # Try extracting JSON from markdown code blocks
    import re

    block_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL)
    if block_match:
        try:
            data = json.loads(block_match.group(1))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    # Fallback: try to find any JSON object in the text
    obj_match = re.search(r"(\{.*\})", response_text, re.DOTALL)
    if obj_match:
        try:
            data = json.loads(obj_match.group(1))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    logger.warning("Could not parse LLM response as JSON, returning partial data")
    return {
        "industry": None,
        "size_estimate": None,
        "tech_stack": [],
        "key_people": [],
        "recent_developments": [],
        "confidence_score": 0,
        "_parse_error": f"Could not parse response: {response_text[:200]}",
    }


def enrich_company(text: str, llm_config: Dict[str, Any]) -> Dict[str, Any]:
    """Send scraped text to the LLM and return structured enrichment data.

    Args:
        text: The raw scraped text about the company.
        llm_config: The LLM configuration dictionary (from config.yaml).

    Returns:
        A dict with enrichment fields (industry, size_estimate, tech_stack,
        key_people, recent_developments, confidence_score).

    Raises:
        ValueError: If the LLM API key is missing or invalid.
        requests.RequestException: If the API call fails.
    """
    if not text or not text.strip():
        return {
            "industry": None,
            "size_estimate": None,
            "tech_stack": [],
            "key_people": [],
            "recent_developments": [],
            "confidence_score": 0,
            "_note": "No scraped text available to enrich",
        }

    api_key = _resolve_api_key(llm_config)
    endpoint = llm_config.get(
        "endpoint", "https://api.openai.com/v1"
    ).rstrip("/")
    model = llm_config.get("model", "gpt-4o-mini")
    temperature = llm_config.get("temperature", 0.1)

    url = f"{endpoint}/chat/completions"
    payload = _build_payload(text, model, temperature)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    logger.info("Sending enrichment request to %s with model %s", endpoint, model)
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()

    result = resp.json()
    choices = result.get("choices", [])
    if not choices:
        raise ValueError("LLM API returned no choices")

    content = choices[0].get("message", {}).get("content", "")
    if not content:
        raise ValueError("LLM API returned empty message content")

    return _parse_llm_response(content)
