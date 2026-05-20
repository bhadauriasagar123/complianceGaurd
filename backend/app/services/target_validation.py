"""Target validation with anti-SSRF and network safety controls."""

import ipaddress
import re
import socket
from urllib.parse import urlparse

import validators

from app.core.config import get_settings

BLOCKED_HOSTNAMES = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",  # nosec B104 — blocked host in denylist, not a bind address
    "::1",
    "metadata.google.internal",
    "169.254.169.254",
    "metadata.azure.com",
    "metadata.aws",
}

METADATA_PATTERNS = [
    re.compile(r"169\.254\.\d+\.\d+"),
    re.compile(r"metadata", re.I),
    re.compile(r"instance-data", re.I),
]

PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("169.254.0.0/16"),
]


class TargetValidationError(Exception):
    def __init__(self, message: str, code: str = "INVALID_TARGET") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


class TargetValidator:
    def __init__(self) -> None:
        self.settings = get_settings()

    def normalize_target(self, target: str, target_type: str) -> str:
        target = target.strip().lower()
        if target_type == "url":
            if not target.startswith(("http://", "https://")):
                target = f"https://{target}"
            parsed = urlparse(target)
            if parsed.scheme not in ("http", "https"):
                raise TargetValidationError("Only HTTP/HTTPS URLs are allowed")
            return f"{parsed.scheme}://{parsed.netloc}{parsed.path or ''}".rstrip("/")
        if target_type == "domain":
            if target.startswith(("http://", "https://")):
                parsed = urlparse(target)
                return parsed.netloc.lower()
            return target.lower()
        return target

    def validate(self, target: str, target_type: str) -> str:
        normalized = self.normalize_target(target, target_type)

        if target_type == "url":
            if not validators.url(normalized):
                raise TargetValidationError("Invalid URL format")
            host = urlparse(normalized).hostname
        elif target_type == "domain":
            if not validators.domain(normalized.split("/")[0]):
                raise TargetValidationError("Invalid domain format")
            host = normalized.split("/")[0]
        elif target_type in ("ip", "cidr"):
            host = normalized
            try:
                if "/" in host:
                    network = ipaddress.ip_network(host, strict=False)
                    if self.settings.scan_deny_private_ips:
                        self._check_ip_blocked(network.network_address)
                    return str(network)
                addr = ipaddress.ip_address(host)
                if self.settings.scan_deny_private_ips:
                    self._check_ip_blocked(addr)
                return str(addr)
            except ValueError as exc:
                raise TargetValidationError("Invalid IP or CIDR") from exc
        else:
            raise TargetValidationError(f"Unsupported target type: {target_type}")

        if host:
            self._validate_host(host)

        return normalized

    def _validate_host(self, host: str) -> None:
        host_lower = host.lower().strip("[]")

        if self.settings.scan_deny_localhost and host_lower in BLOCKED_HOSTNAMES:
            raise TargetValidationError("Localhost targets are not permitted", "BLOCKED_LOCALHOST")

        for pattern in METADATA_PATTERNS:
            if pattern.search(host_lower):
                raise TargetValidationError("Cloud metadata endpoints are blocked", "BLOCKED_METADATA")

        if self.settings.scan_deny_metadata and "metadata" in host_lower:
            raise TargetValidationError("Metadata endpoints are blocked", "BLOCKED_METADATA")

        try:
            resolved_ips = socket.getaddrinfo(host_lower, None)
            for result in resolved_ips:
                ip_str = result[4][0]
                try:
                    addr = ipaddress.ip_address(ip_str)
                    if self.settings.scan_deny_private_ips:
                        self._check_ip_blocked(addr)
                except ValueError:
                    continue
        except socket.gaierror:
            pass

    def _check_ip_blocked(self, addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> None:
        for network in PRIVATE_NETWORKS:
            if addr in network:
                raise TargetValidationError(
                    "Private/internal network addresses are not permitted",
                    "BLOCKED_PRIVATE_IP",
                )
