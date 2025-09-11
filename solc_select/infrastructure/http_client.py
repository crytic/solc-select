"""
HTTP client configuration for solc-select.

This module provides centralized HTTP client configuration with
retry logic and proper timeout handling.
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def create_http_session() -> requests.Session:
    """Create a new HTTP session with retry logic for rate limits and server errors."""
    session = requests.Session()

    # Configure retry strategy for 429s and server errors
    retry_strategy = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Set standard timeouts (connect_timeout, read_timeout)
    # Note: Session.timeout is not a standard attribute, but we'll add it as a custom attribute
    session.timeout = (10, 60)  # type: ignore[attr-defined]  # 10s connection, 60s read for downloads

    return session
