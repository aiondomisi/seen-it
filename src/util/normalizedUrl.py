from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

TRACKING_PARAMS = {
    "fbclid",
    "gclid",
    "igshid",
    "igsh",
    "mc_cid",
    "mc_eid",
    "ref",
    "ref_src",
    "ref_url",
    "s",
    "si",
    "t",
    "feature",
    "mibextid",
    "rdid",
    "share_url",
    "share_id",
}
TRACKING_PREFIXES = ("utm_",)

# Frontends/mirrors mapped to the canonical host
HOST_ALIASES = {
    "twitter.com": "x.com",
    "mobile.twitter.com": "x.com",
    "fxtwitter.com": "x.com",
    "vxtwitter.com": "x.com",
    "fixupx.com": "x.com",
    "m.youtube.com": "youtube.com",
    "music.youtube.com": "youtube.com",
    "youtu.be": "youtube.com",
    "ddinstagram.com": "instagram.com",
    "m.facebook.com": "facebook.com",
    "web.facebook.com": "facebook.com",
}


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())

    host = (parts.hostname or "").lower().removeprefix("www.")
    host = HOST_ALIASES.get(host, host)

    # keep non-default ports only
    if parts.port and parts.port not in (80, 443):
        host = f"{host}:{parts.port}"

    path = parts.path
    # youtu.be/<id> -> youtube.com/watch?v=<id>
    query_items = parse_qsl(parts.query, keep_blank_values=True)
    if urlsplit(url.strip()).hostname == "youtu.be" and path.strip("/"):
        query_items.append(("v", path.strip("/")))
        path = "/watch"

    path = path.rstrip("/") or "/"

    query = sorted(
        (k, v)
        for k, v in query_items
        if k.lower() not in TRACKING_PARAMS
        and not k.lower().startswith(TRACKING_PREFIXES)
    )

    # force https, drop fragment
    return urlunsplit(("https", host, path, urlencode(query), ""))
