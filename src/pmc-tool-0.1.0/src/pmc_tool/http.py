from __future__ import annotations

import json
import random
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class HttpClient:
    def __init__(self, user_agent: str, timeout: float = 30.0) -> None:
        self.user_agent = user_agent
        self.timeout = timeout

    def get_json(self, url: str, params: dict[str, Any] | None = None) -> Any:
        query = urlencode({k: v for k, v in (params or {}).items() if v is not None})
        request_url = f"{url}?{query}" if query else url
        request = Request(request_url, headers={"User-Agent": self.user_agent})
        backoff = 1.0
        for attempt in range(5):
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    return json.loads(response.read().decode("utf-8"))
            except HTTPError as exc:
                if exc.code not in {429, 500, 502, 503, 504} or attempt == 4:
                    raise RuntimeError(f"Request failed with HTTP {exc.code}: {request_url}") from exc
            except URLError as exc:
                if attempt == 4:
                    raise RuntimeError(f"Request failed: {request_url}") from exc
            time.sleep(backoff + random.uniform(0.0, 0.25 * backoff))
            backoff = min(backoff * 2, 8.0)
