import os
import time
import json
import urllib.parse
import httpx

ELLUCIAN_AUTH_URL = "https://integrate.elluciancloud.com/auth"
ETHOS_ACCEPT = "application/json"

_token_cache = {"token": None, "expires_at": 0.0}


async def get_api_token(client: httpx.AsyncClient) -> str:
    api_key = os.environ["TEST_API_KEY"]  # or whichever you want
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires_at"]:
        return _token_cache["token"]

    resp = await client.post(
        ELLUCIAN_AUTH_URL,
        headers={"Accept": "application/json",
                 "Authorization": f"Bearer {api_key}"},
    )
    resp.raise_for_status()
    _token_cache["token"] = resp.text.strip()
    _token_cache["expires_at"] = now + 280
    return _token_cache["token"]


def encode_params(base, criteria_obj):
    s = json.dumps(criteria_obj, separators=(",", ":"))
    return f"{base}?criteria={urllib.parse.quote(s, safe='')}"


def build_request_url(ep) -> str:
    if getattr(ep, "path_suffix", None):
        return f"{ep.url.rstrip('/')}/{ep.path_suffix.lstrip('/')}"

    criteria = (ep.params or {}).get("criteria")
    if criteria:
        return encode_params(ep.url, criteria)

    return ep.url
