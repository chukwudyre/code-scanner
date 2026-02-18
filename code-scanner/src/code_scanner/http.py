from __future__ import annotations

import json
import os
import ssl
from dataclasses import dataclass
from typing import Any
from urllib import error, request

try:
    import certifi
except ImportError:  # pragma: no cover - optional dependency
    certifi = None


@dataclass(frozen=True)
class HttpResponse:
    status: int
    headers: dict[str, str]
    data: Any


def get_json(url: str, headers: dict[str, str] | None = None, timeout: int = 30) -> HttpResponse:
    req = request.Request(url=url, headers=headers or {}, method="GET")
    context = _build_ssl_context()
    try:
        with request.urlopen(req, timeout=timeout, context=context) as response:
            body = response.read().decode("utf-8")
            payload = json.loads(body)
            normalized_headers = {k.lower(): v for k, v in response.headers.items()}
            return HttpResponse(
                status=response.status,
                headers=normalized_headers,
                data=payload,
            )
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} for {url}: {detail[:400]}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Failed request to {url}: {exc.reason}") from exc


def _build_ssl_context() -> ssl.SSLContext:
    if _env_true("CODE_SCANNER_INSECURE_SKIP_VERIFY"):
        return ssl._create_unverified_context()

    bundle = (
        os.getenv("CODE_SCANNER_CA_BUNDLE")
        or os.getenv("SSL_CERT_FILE")
        or os.getenv("REQUESTS_CA_BUNDLE")
    )
    if bundle:
        return ssl.create_default_context(cafile=bundle)

    if certifi is not None:
        return ssl.create_default_context(cafile=certifi.where())

    return ssl.create_default_context()


def _env_true(name: str) -> bool:
    value = (os.getenv(name) or "").strip().lower()
    return value in {"1", "true", "yes", "on"}
