"""
HTTP client configuration for solc-select.

This module provides centralized HTTP client configuration with
retry logic and proper timeout handling.
"""

from typing import Any, Mapping, Optional, Tuple, Union

import requests
from requests.adapters import HTTPAdapter
from requests.models import PreparedRequest, Response
from urllib3.util.retry import Retry


class TimeoutHTTPAdapter(HTTPAdapter):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.timeout = kwargs.pop("timeout", None)
        super().__init__(*args, **kwargs)

    def send(
        self,
        request: PreparedRequest,
        stream: bool = False,
        timeout: Union[float, Tuple[float, float], Tuple[float, None], None] = None,
        verify: Union[bool, str] = True,
        cert: Union[bytes, str, Tuple[Union[bytes, str], Union[bytes, str]], None] = None,
        proxies: Optional[Mapping[str, str]] = None,
    ) -> Response:
        timeout = timeout or self.timeout
        return super().send(
            request, stream=stream, timeout=timeout, verify=verify, cert=cert, proxies=proxies
        )


def create_http_session() -> requests.Session:
    """Create a new HTTP session with retry logic for rate limits and server errors."""
    session = requests.Session()

    # Configure retry strategy for 429s and server errors
    retry_strategy = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )

    adapter = TimeoutHTTPAdapter(timeout=(10, 30), max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session
