from __future__ import annotations
import time
import httpx
import secrets
import json
import urllib.parse
import os
from dataclasses import dataclass
from typing import Any, Optional
from unittest import result
from fastapi import FastAPI
from fastapi import Depends, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()

DASH_USER = os.getenv("DASH_USER")
DASH_PASS = os.getenv("DASH_PASS")
if not DASH_USER or not DASH_PASS:
    raise RuntimeError("DASH_USER / DASH_PASS not set")


def require_basic_auth(credentials: HTTPBasicCredentials = Depends(security)):
    correct_user = secrets.compare_digest(credentials.username, DASH_USER)
    correct_pass = secrets.compare_digest(credentials.password, DASH_PASS)

    if not (correct_user and correct_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username


api_key = os.getenv("test_api_key")
if not api_key:
    raise RuntimeError("test_api_key not set")

app = FastAPI(title="API Monitor POC")

_token_cache = {
    "token": None,
    "expires_at": 0.0,
}

ELLUCIAN_AUTH_URL = "https://integrate.elluciancloud.com/auth"


async def get_api_token(client: httpx.AsyncClient) -> str:
    now = time.time()

    # Reuse cached token if still valid
    if _token_cache["token"] and now < _token_cache["expires_at"]:
        return _token_cache["token"]

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    resp = await client.post(ELLUCIAN_AUTH_URL, headers=headers)
    resp.raise_for_status()

    token = resp.text.strip()

    _token_cache["token"] = token
    _token_cache["expires_at"] = now + 280

    return token


def encode_params(base, criteria_obj):
    s = json.dumps(criteria_obj, separators=(",", ":"))
    return f"{base}?criteria={urllib.parse.quote(s, safe='')}"


@dataclass
class Endpoint:
    name: str
    url: str
    params: dict
    headers: Optional[dict[str, str]] = None
    method: str = "GET"
    timeout_s: float = 30.0
    require_non_empty_body: bool = True
    needs_bearer_token: bool = True


ENDPOINTS: list[Endpoint] = [
    Endpoint(
        name="Persons Endpoint with BannerId Criteria",
        url="https://integrate.elluciancloud.com/api/persons",
        params={
            "criteria": {
                "credentials": [
                    {"type": "bannerId", "value": "M00251282"}
                ]
            }
        },
        needs_bearer_token=True,
    )]


# eventually connect to a lightweight db??
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
    }

    try:
        headers = dict(ep.headers or {})

        token = await get_api_token(client)
        headers["Authorization"] = f"Bearer {token}"
        headers["Accept"] = "application/json"

        resp = await client.request(
            ep.method,
            encode_params(ep.url, ep.params.get("criteria", {})),
            headers=headers,
            timeout=ep.timeout_s,
        )

        result["request"] = {
            "method": ep.method,
            "url": str(resp.request.url),
            "headers": {"Accept": headers["Accept"]},
        }

        latency_ms = int((time.perf_counter() - t0) * 1000)
        body = resp.text or ""
        body_len = len(body)

        result.update(
            {
                "status_code": resp.status_code,
                "latency_ms": latency_ms,
                "body_len": body_len,
            }
        )

        # response code checking
        if resp.status_code < 200 or resp.status_code >= 300:
            result["ok"] = False
            result["reason"] = f"HTTP {resp.status_code}"
            return result

        if ep.require_non_empty_body and body_len == 0:
            result["ok"] = False
            result["reason"] = "200 but empty body"
            return result

        result["ok"] = True
        result["reason"] = "OK"
        return result

    except httpx.TimeoutException:
        result["latency_ms"] = int((time.perf_counter() - t0) * 1000)
        result["ok"] = False
        result["reason"] = "timeout"
        return result

    except Exception as e:
        result["latency_ms"] = int((time.perf_counter() - t0) * 1000)
        result["ok"] = False
        result["reason"] = f"error: {type(e).__name__}"
        return result


@app.on_event("startup")
async def startup() -> None:
    await run_checks_once()


async def run_checks_once() -> None:
    async with httpx.AsyncClient(follow_redirects=True) as client:
        for ep in ENDPOINTS:
            res = await check_endpoint(client, ep)
            LATEST[ep.name] = res


@app.get("/api/status")
async def api_status(user: str = Depends(require_basic_auth)):
    await run_checks_once()
    return JSONResponse({"results": list(LATEST.values())})


@app.get("/", response_class=HTMLResponse)
async def home(user: str = Depends(require_basic_auth)):
    return """
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>API Monitor POC</title>
  <style>
    body { font-family: Segoe UI, Arial, sans-serif; margin: 16px; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border-bottom: 1px solid #ddd; padding: 8px; text-align: left; }
    th { position: sticky; top: 0; background: #f7f7f7; }
    .ok { font-weight: 600; }
    .bad { font-weight: 600; }
    .muted { color: #666; font-size: 0.9em; }
  </style>
</head>
<body>
  <h2>API Monitor POC</h2>
  <div class="muted">Tests endpoints every 30 seconds</div>
  <p><button onclick="loadData()">Refresh now</button></p>
  <table>
    <thead>
      <tr>
        <th>Status</th>
        <th>Name</th>
        <th>HTTP</th>
        <th>Latency (ms)</th>
        <th>Body</th>
        <th>Checked</th>
        <th>Reason</th>
      </tr>
    </thead>
    <tbody id="rows"></tbody>
  </table>

<script>
async function loadData() {
  const r = await fetch('/api/status');
  const j = await r.json();
  const rows = document.getElementById('rows');
  rows.innerHTML = '';

  for (const item of j.results) {
    const statusIcon = item.ok ? '✅' : '❌';
    const tr = document.createElement('tr');
    tr.innerHTML = `
        <td class="${item.ok ? 'ok' : 'bad'}">${statusIcon}</td>
        <td>
            <div>${item.name}</div>
            <div class="muted"
                title="${item.request?.url ?? ''}"
                style="cursor: help; word-break: break-all;">
            ${item.url}
            </div>
        </td>
        <td>${item.status_code ?? ''}</td>
        <td>${item.latency_ms ?? ''}</td>
        <td>${item.body_len ?? ''}</td>
        <td>${item.ts ?? ''}</td>
        <td>${item.reason ?? ''}</td>
        `;
    rows.appendChild(tr);
  }
}

loadData();
setInterval(loadData, 30000);
</script>
</body>
</html>
"""


# manual trigger
@app.post("/api/run")
async def run_now() -> JSONResponse:
    await run_checks_once()
    return JSONResponse({"ok": True, "count": len(LATEST)})
