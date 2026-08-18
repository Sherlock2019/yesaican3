"""Single source of truth for service endpoints.

The API port was previously declared in three places that disagreed:
newstart.sh used 9100, Challenge Hub fell back to 8090, and anything launched
outside the boot script silently talked to a port nothing listened on. Import
from here instead of hardcoding.
"""

from __future__ import annotations

import os

__all__ = ["DEFAULT_API_PORT", "api_base_url", "api_endpoint"]

DEFAULT_API_PORT = 9100
DEFAULT_API_HOST = "localhost"


def api_base_url() -> str:
    """Base URL for the internal API.

    ``API_URL`` wins when set (newstart.sh exports it); otherwise the URL is
    assembled from ``APIPORT``/``API_PORT`` so the fallback tracks the boot
    script rather than drifting from it.
    """
    explicit = (os.getenv("API_URL") or "").strip()
    if explicit:
        return explicit.rstrip("/")
    port = (os.getenv("APIPORT") or os.getenv("API_PORT") or "").strip()
    try:
        port_number = int(port) if port else DEFAULT_API_PORT
    except ValueError:
        port_number = DEFAULT_API_PORT
    host = (os.getenv("API_HOST") or DEFAULT_API_HOST).strip() or DEFAULT_API_HOST
    return f"http://{host}:{port_number}"


def api_endpoint(path: str) -> str:
    return f"{api_base_url().rstrip('/')}/{str(path or '').lstrip('/')}"
