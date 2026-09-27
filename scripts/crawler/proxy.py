"""Qingguo proxy resolution and TLS context — infrastructure, not accounts.

The proxy endpoint is a single infra credential and stays in the environment
(X_PROXY / QINGGUO_PROXY_URL / SOCIAL_PROXY_URL). Accounts are dynamic data and
live in the pool file instead. Each account session opens its own connection, and
per the probe on 2026-09-14 the exit IP is bound to the connection, so one
account keeps a stable IP for its whole crawl.
"""
from __future__ import annotations

import os
import ssl
from pathlib import Path
from urllib.parse import urlsplit

PROXY_KEYS = ("QINGGUO_PROXY_URL", "SOCIAL_PROXY_URL", "X_PROXY")


def load_env(root: Path) -> None:
    """Populate os.environ from local .env files without overriding real env."""
    for name in (".env", ".agents/skills/social-qingguo-collector/.env"):
        path = root / name
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def proxy_url() -> str:
    for key in PROXY_KEYS:
        value = os.environ.get(key, "").strip()
        if not value:
            continue
        try:
            parts = urlsplit(value)
            valid = parts.scheme in ("http", "https") and parts.hostname and parts.port
        except ValueError:
            valid = False
        if not valid:
            raise RuntimeError("Invalid proxy URL: expected http(s)://username:password@host:port")
        if parts.hostname == "overseas.tunnel.qg.net" and parts.scheme != "https":
            raise RuntimeError("Qingguo overseas endpoint requires an https:// proxy URL")
        return value
    raise RuntimeError("Qingguo proxy is not configured. Set X_PROXY (or QINGGUO_PROXY_URL/SOCIAL_PROXY_URL).")


def proxy_ssl_context(proxy: str) -> ssl.SSLContext:
    """Verify the TLS chain but tolerate Qingguo's known hostname mismatch.

    Qingguo's *.qg.net certificate does not cover overseas.tunnel.qg.net. Only the
    proxy handshake relaxes hostname checking; the target site (x.com) still uses
    full default verification through the same client.
    """
    context = ssl.create_default_context()
    host = urlsplit(proxy).hostname or ""
    if host.endswith(".tunnel.qg.net") or host == "tunnel.qg.net":
        context.check_hostname = False
    return context
