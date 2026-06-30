from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


def is_safe_http_url(url: str) -> bool:
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"}:
        return False
    if not parsed.netloc:
        return False
    return True


def is_private_address(host: str) -> bool:
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return True

    for info in infos:
        sockaddr = info[4][0]
        try:
            ip = ipaddress.ip_address(sockaddr)
        except ValueError:
            return True
        if any(
            [
                ip.is_private,
                ip.is_loopback,
                ip.is_link_local,
                ip.is_multicast,
                ip.is_reserved,
                ip.is_unspecified,
            ]
        ):
            return True
    return False
