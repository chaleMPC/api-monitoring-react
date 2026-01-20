from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class Endpoint:
    name: str
    url: str
    params: Optional[dict[str, Any]] = None
    path_suffix: Optional[str] = None
    headers: Optional[dict[str, str]] = None
    method: str = "GET"
    timeout_s: float = 30.0
    require_non_empty_body: bool = True
    needs_bearer_token: bool = True
