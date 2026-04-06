from __future__ import annotations

import json
import random
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
import tempfile
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class HttpResponse:
    url: str
    status: int
    headers: dict[str, str]
    body: bytes

    @property
    def content_type(self) -> str:
        return self.headers.get("Content-Type", "")

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")

    def json(self) -> Any:
        return json.loads(self.text)


class HttpClient:
    def __init__(self, user_agent: str, timeout: float = 30.0) -> None:
        self.user_agent = user_agent
        self.timeout = timeout

    def request(
        self,
        *,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
        form: dict[str, Any] | None = None,
        json_body: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> HttpResponse:
        query = urlencode({k: v for k, v in (params or {}).items() if v is not None}, doseq=True)
        request_url = f"{url}?{query}" if query else url

        request_headers = {"User-Agent": self.user_agent}
        if headers:
            request_headers.update(headers)

        data: bytes | None = None
        if form is not None and json_body is not None:
            raise ValueError("Only one of form or json_body may be set")
        if form is not None:
            request_headers["Content-Type"] = "application/x-www-form-urlencoded"
            data = urlencode({k: v for k, v in form.items() if v is not None}, doseq=True).encode(
                "utf-8"
            )
        elif json_body is not None:
            request_headers["Content-Type"] = "application/json"
            data = json.dumps(json_body, ensure_ascii=True).encode("utf-8")

        request = Request(request_url, data=data, headers=request_headers, method=method.upper())
        backoff = 1.0
        for attempt in range(5):
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    response_headers = dict(response.headers.items())
                    return HttpResponse(
                        url=request_url,
                        status=getattr(response, "status", response.getcode()),
                        headers=response_headers,
                        body=response.read(),
                    )
            except HTTPError as exc:
                if exc.code not in {429, 500, 502, 503, 504} or attempt == 4:
                    detail = exc.read().decode("utf-8", errors="replace").strip()
                    suffix = f" Body: {detail}" if detail else ""
                    raise RuntimeError(
                        f"Request failed with HTTP {exc.code}: {request_url}.{suffix}"
                    ) from exc
            except URLError as exc:
                if attempt == 4:
                    try:
                        return self._request_with_curl(
                            method=method.upper(),
                            request_url=request_url,
                            headers=request_headers,
                            data=data,
                        )
                    except RuntimeError as curl_exc:
                        raise RuntimeError(f"Request failed: {request_url}") from curl_exc
            time.sleep(backoff + random.uniform(0.0, 0.25 * backoff))
            backoff = min(backoff * 2, 8.0)
        raise RuntimeError(f"Request failed: {request_url}")

    def get_json(self, url: str, params: dict[str, Any] | None = None) -> Any:
        return self.request(method="GET", url=url, params=params).json()

    def _request_with_curl(
        self,
        *,
        method: str,
        request_url: str,
        headers: dict[str, str],
        data: bytes | None,
    ) -> HttpResponse:
        with tempfile.TemporaryDirectory() as tempdir:
            header_path = Path(tempdir) / "headers.txt"
            body_path = Path(tempdir) / "body.bin"
            command = [
                "curl",
                "-sS",
                "-L",
                "-X",
                method,
                "-D",
                str(header_path),
                "-o",
                str(body_path),
            ]
            for key, value in headers.items():
                command.extend(["-H", f"{key}: {value}"])
            if data is not None:
                command.extend(["--data-binary", "@-"])
            command.append(request_url)
            completed = subprocess.run(
                command,
                input=data,
                capture_output=True,
                check=False,
            )
            if completed.returncode != 0:
                detail = completed.stderr.decode("utf-8", errors="replace").strip()
                raise RuntimeError(detail or f"curl failed for {request_url}")

            raw_headers = header_path.read_text(encoding="utf-8", errors="replace").strip()
            header_blocks = [block for block in raw_headers.split("\r\n\r\n") if block.strip()]
            final_block = header_blocks[-1] if header_blocks else ""
            lines = [line for line in final_block.splitlines() if line.strip()]
            status = 200
            parsed_headers: dict[str, str] = {}
            if lines:
                parts = lines[0].split()
                if len(parts) >= 2 and parts[1].isdigit():
                    status = int(parts[1])
                for line in lines[1:]:
                    if ":" in line:
                        key, value = line.split(":", 1)
                        parsed_headers[key.strip()] = value.strip()
            body = body_path.read_bytes()
            if status >= 400:
                detail = body.decode("utf-8", errors="replace").strip()
                suffix = f" Body: {detail}" if detail else ""
                raise RuntimeError(f"Request failed with HTTP {status}: {request_url}.{suffix}")
            return HttpResponse(
                url=request_url,
                status=status,
                headers=parsed_headers,
                body=body,
            )
