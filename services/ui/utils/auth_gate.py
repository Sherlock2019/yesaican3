"""Authentication gate for the YES AI CAN Lab UI.

Modes are chosen with ``YESAICAN_AUTH_MODE``:

* ``off``      — no gate (the historical behaviour, and the default so that
                 upgrading this file can never lock an operator out).
* ``password`` — one shared secret from ``YESAICAN_AUTH_PASSWORD``. Good enough
                 to keep an internal tool off the open internet; it identifies
                 nobody, so treat submissions as pseudonymous.
* ``proxy``    — trust an authenticated reverse proxy that injects a user
                 header (``YESAICAN_AUTH_HEADER``, default ``X-Forwarded-User``).
                 This is the mode to pair with SSO.

IMPORTANT: Streamlit serves every file in ``pages/`` as its own URL, and only a
handful of this app's 62 pages share a common entry point. An in-app gate is
therefore a speed bump, not a boundary — any page that forgets to call
``require_auth()`` is reachable directly. The durable fix is to require auth at
the reverse proxy so no request reaches Streamlit unauthenticated; see
``deploy/nginx-auth.conf.example``. Use ``proxy`` mode together with that, so
the app knows who the proxy let in.
"""

from __future__ import annotations

import hmac
import os
from typing import Any

import streamlit as st

__all__ = ["auth_mode", "current_user", "require_auth"]

_SESSION_KEY = "auth_user"


def auth_mode() -> str:
    mode = os.getenv("YESAICAN_AUTH_MODE", "off").strip().lower()
    return mode if mode in {"off", "password", "proxy"} else "off"


def current_user() -> dict | None:
    user = st.session_state.get(_SESSION_KEY)
    return user if isinstance(user, dict) else None


def _request_headers() -> dict[str, Any]:
    """Inbound headers, when the Streamlit version exposes them."""
    try:
        context = getattr(st, "context", None)
        headers = getattr(context, "headers", None) if context else None
        if headers:
            return {str(key).lower(): value for key, value in dict(headers).items()}
    except Exception:
        pass
    return {}


def _deny(message: str) -> None:
    st.error(message)
    st.stop()


def _require_proxy_identity() -> dict:
    header_name = os.getenv("YESAICAN_AUTH_HEADER", "X-Forwarded-User").strip().lower()
    value = str(_request_headers().get(header_name, "")).strip()
    if not value:
        _deny(
            f"Sign-in required. This deployment expects the `{header_name}` header from an "
            "authenticating proxy, and the request did not carry one. If you reached this "
            "page directly, go through the normal internal URL."
        )
    user = {"name": value.split("@")[0], "email": value, "method": "proxy"}
    st.session_state[_SESSION_KEY] = user
    return user


def _require_password() -> dict:
    secret = os.getenv("YESAICAN_AUTH_PASSWORD", "")
    if not secret:
        # Fail closed: a password mode with no password configured is a
        # misconfiguration, and defaulting to "open" would hide it.
        _deny(
            "Access is misconfigured: YESAICAN_AUTH_MODE=password but YESAICAN_AUTH_PASSWORD "
            "is unset, so the app cannot verify anyone. Set the variable and restart."
        )

    st.markdown("### 🔒 YES AI CAN Lab")
    st.caption("This workspace holds internal pain points. Enter the team access code to continue.")
    with st.form("yesaican_auth_form"):
        name = st.text_input("Your name", placeholder="So contributions are attributed to you")
        code = st.text_input("Access code", type="password")
        if st.form_submit_button("Enter", use_container_width=True):
            if hmac.compare_digest(code, secret):
                user = {"name": name.strip() or "Racker", "email": "", "method": "password"}
                st.session_state[_SESSION_KEY] = user
                st.rerun()
            else:
                st.error("That access code is not right. Check with the lab team.")
    st.stop()


def require_auth() -> dict | None:
    """Gate the current page. Returns the signed-in user, or None when mode is off."""
    mode = auth_mode()
    if mode == "off":
        return None
    existing = current_user()
    if existing:
        return existing
    return _require_proxy_identity() if mode == "proxy" else _require_password()
