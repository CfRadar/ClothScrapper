import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import httpx

ALLOWLISTED_HOSTS = {
    "amazon.in",
    "www.amazon.in",
    "completion.amazon.in",
    "myntra.com",
    "www.myntra.com",
    "flipkart.com",
    "www.flipkart.com",
    "reddit.com",
    "www.reddit.com",
    "openrouter.ai",
}


class SSRFError(ValueError):
    """Raised when an outbound URL violates SSRF host or IP security restrictions."""

    pass


def validate_url(url: str, allow_http_for_testing: bool = False) -> None:
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()

    if allow_http_for_testing:
        if scheme not in ("http", "https"):
            raise SSRFError(f"Invalid URL scheme '{scheme}'. Only http and https are permitted.")
    else:
        if scheme != "https":
            raise SSRFError(f"Invalid URL scheme '{scheme}'. Only https is permitted.")

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise SSRFError("URL is missing a valid hostname.")

    if hostname not in ALLOWLISTED_HOSTS:
        raise SSRFError(f"Host '{hostname}' is not in the outbound allowlist.")

    # Resolve hostname to verify destination IP is not private/loopback/multicast
    try:
        addr_info = socket.getaddrinfo(hostname, None)
    except socket.gaierror as err:
        raise SSRFError(f"Failed to resolve host '{hostname}': {err}") from err

    for family, _, _, _, sockaddr in addr_info:
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue

        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise SSRFError(
                f"Resolved IP {ip_str} for host '{hostname}' is non-routable, private, or loopback."
            )


class SafeAsyncClient:
    """Outbound HTTPX client enforcing strict host allowlisting and DNS SSRF protections."""

    def __init__(self, timeout: float = 15.0, **kwargs):
        self.timeout = timeout
        self.client_kwargs = kwargs
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            timeout=self.timeout, follow_redirects=False, **self.client_kwargs
        )
        await self._client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.__aexit__(exc_type, exc_val, exc_tb)

    async def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        current_url = url
        redirect_count = 0
        max_redirects = kwargs.pop("max_redirects", 3)

        if not self._client:
            self._client = httpx.AsyncClient(timeout=self.timeout, follow_redirects=False)

        while True:
            validate_url(current_url)
            resp = await self._client.request(method, current_url, **kwargs)

            if resp.status_code in (301, 302, 303, 307, 308):
                location = resp.headers.get("Location")
                if not location:
                    return resp

                redirect_count += 1
                if redirect_count > max_redirects:
                    raise SSRFError(f"Exceeded maximum allowed redirects ({max_redirects}).")

                # Resolve relative redirects against current URL
                current_url = urljoin(current_url, location)
                # Re-validate redirected URL (ensures redirect cannot bounce to intranet or unapproved host)
                validate_url(current_url)

                # For 303 or 301/302 from POST, standard behavior switches to GET
                if resp.status_code == 303 or (
                    resp.status_code in (301, 302) and method.upper() == "POST"
                ):
                    method = "GET"
                    kwargs.pop("json", None)
                    kwargs.pop("content", None)
                    kwargs.pop("data", None)
                continue

            return resp

    async def get(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("POST", url, **kwargs)
