import re
from html import unescape
from urllib.parse import urlsplit
from curl_cffi.requests import AsyncSession
from curl_cffi.requests.exceptions import RequestException

HEAD_UA = "python-requests/2.32.3"
BODY_UA = "Mozilla/5.0 (compatible; Discordbot/2.0; +https://discordapp.com)"
BAD_FIRST_SEGMENTS = {"share", "login", "login.php", "checkpoint", "recover"}

REDIRECT_HOSTS = {
    "fb.watch",
    "vm.tiktok.com",
    "vt.tiktok.com",
    "pin.it",
    "spotify.link",
    "amzn.to",
    "a.co",
    "bit.ly",
    "t.co",
    "lnkd.in",
    "tinyurl.com",
}
# (host, path prefix) for share links on otherwise normal hosts
REDIRECT_PATHS = {
    ("facebook.com", "/share/"),
    ("m.facebook.com", "/share/"),
    ("instagram.com", "/share/"),
    ("tiktok.com", "/t/"),
    ("reddit.com", "/s/"),  # matches /r/<sub>/s/<token> via `in` below
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


def is_facebook(host: str) -> bool:
    return host == "facebook.com" or host.endswith(".facebook.com")


def is_usable_facebook(url: str) -> bool:
    parts = urlsplit(url)
    segments = [s for s in parts.path.split("/") if s]
    return (
        is_facebook((parts.hostname or "").lower())
        and bool(segments)
        and segments[0].lower() not in BAD_FIRST_SEGMENTS
    )


def needs_resolve(url: str) -> bool:
    parts = urlsplit(url)
    host = (parts.hostname or "").lower().removeprefix("www.")
    if host in REDIRECT_HOSTS:
        return True
    return any(host == h and p in parts.path for h, p in REDIRECT_PATHS)


def declared_urls(html: str) -> list[str]:
    patterns = (
        r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)',
        r'<meta[^>]+property=["\']og:url["\'][^>]+content=["\']([^"\']+)',
    )
    return [unescape(m) for p in patterns for m in re.findall(p, html)]


async def resolve_url(url: str) -> str:
    if not needs_resolve(url):
        return url
    try:
        async with AsyncSession(impersonate="chrome", timeout=10) as session:
            host = (urlsplit(url).hostname or "").lower()

            if not is_facebook(host):
                r = await session.get(
                    url, headers={"User-Agent": BODY_UA}, allow_redirects=True
                )
                return str(r.url)

            r = await session.head(
                url, headers={"User-Agent": HEAD_UA}, allow_redirects=True
            )
            if is_usable_facebook(str(r.url)):
                return str(r.url)

            r = await session.get(
                url, headers={"User-Agent": BODY_UA}, allow_redirects=True
            )
            if is_usable_facebook(str(r.url)):
                return str(r.url)
            for candidate in declared_urls(r.text):
                if is_usable_facebook(candidate):
                    return candidate
    except RequestException:
        pass
    return url
