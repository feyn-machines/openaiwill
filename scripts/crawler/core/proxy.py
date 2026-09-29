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
    """Populate os.environ from the project's own .env without overriding real env."""
    for name in (".env",):
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


def transport(proxy: str) -> str:
    """'https' or 'http': how the proxy credential travels to the entry.

    The Qingguo entry answers both on one port. Plain http has run since
    2026-09-29 (user decision, after the entry certificate expired on
    2026-09-27): the proxy credential then crosses the network in the clear,
    while x.com traffic stays end-to-end TLS inside the CONNECT tunnel.
    """
    return urlsplit(proxy).scheme


def entry_report(proxy: str, timeout: float = 15.0):
    """Probe the proxy entry without credentials: a TLS handshake for https,
    an unauthenticated CONNECT for http (a real proxy answers 407).

    For http this also catches the local VPN (Shadowrocket) misrouting a
    domain-addressed plain-http connection (seen as a Cloudflare 400). Qingguo
    must still leave through that VPN, so the entry is addressed by its IP
    (overseas.tunnel.qg.net -> overseas-us -> 23.236.65.26 on 2026-09-29).
    """
    if transport(proxy) == "https":
        return certificate_report(proxy, timeout)
    import socket
    parts = urlsplit(proxy)
    try:
        with socket.create_connection((parts.hostname, parts.port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            sock.sendall(b"CONNECT x.com:443 HTTP/1.1\r\nHost: x.com:443\r\n\r\n")
            reply = sock.recv(512).decode("latin-1")
    except OSError as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    status = reply.split("\r\n", 1)[0]
    if " 407 " in f"{status} " or "proxy-authenticate" in reply.lower():
        return {"ok": True, "not_after": None, "days_left": None, "note": "plain http proxy entry answers"}
    return {"ok": False, "error": f"entry did not answer as a proxy ({status or 'no reply'}); "
                                  "if the VPN misroutes the domain, address the entry by its IP"}


def certificate_report(proxy: str, timeout: float = 15.0):
    """Open a TLS handshake to the proxy entry (no credentials sent) and report
    its certificate: {"ok", "not_after", "days_left"} or {"ok": False, "error"}.

    Uses the same context as the crawler, so an expired or untrusted proxy
    certificate shows up here before a run spends its retries on it.
    """
    import socket
    from datetime import datetime, timezone
    parts = urlsplit(proxy)
    context = proxy_ssl_context(proxy)
    try:
        with socket.create_connection((parts.hostname, parts.port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=parts.hostname) as tls:
                cert = tls.getpeercert()
    except (OSError, ssl.SSLError) as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    not_after = datetime.fromtimestamp(ssl.cert_time_to_seconds(cert["notAfter"]), timezone.utc)
    return {"ok": True, "not_after": not_after.isoformat(),
            "days_left": (not_after - datetime.now(timezone.utc)).days}

