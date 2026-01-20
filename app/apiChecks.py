import time
import httpx
from typing import Any
from app.structures import Endpoint
from app.ellucianHelpers import get_api_token, ETHOS_ACCEPT, build_request_url
from app.endpoints import ENDPOINTS


LATEST: dict[str, dict[str, Any]] = {}


async def check_endpoint(client: httpx.AsyncClient, ep: Endpoint) -> dict[str, Any]:
    t0 = time.perf_counter()
    result: dict[str, Any] = {
        "name": ep.name,
        "url": ep.url,
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "status_code": None,
        "latency_ms": None,
        "body_len": None,
        "ok": False,
        "reason": "",
        "request": None,
    }

    headers = {"Accept": ETHOS_ACCEPT}
    if ep.needs_bearer_token:
        headers["Authorization"] = f"Bearer {await get_api_token(client)}"

    try:
        resp = await client.request(
            ep.method,
            build_request_url(ep),
            headers=headers,
            timeout=ep.timeout_s
        )

        result["request"] = {"method": ep.method, "url": str(resp.request.url)}
        result["status_code"] = resp.status_code
        result["latency_ms"] = int((time.perf_counter() - t0) * 1000)

        body = resp.text or ""
        result["body_len"] = len(body)

        if resp.status_code < 200 or resp.status_code >= 300:
            result["reason"] = f"HTTP {resp.status_code}"
            return result

        result["ok"] = True
        result["reason"] = "OK"
        return result

    except httpx.TimeoutException:
        result["latency_ms"] = int((time.perf_counter() - t0) * 1000)
        result["reason"] = "timeout"
        return result
    except Exception as e:
        result["latency_ms"] = int((time.perf_counter() - t0) * 1000)
        result["reason"] = f"error: {type(e).__name__}: {e}"
        return result


async def run_checks_once() -> None:
    async with httpx.AsyncClient(follow_redirects=True) as client:
        for ep in ENDPOINTS:
            LATEST[ep.name] = await check_endpoint(client, ep)
