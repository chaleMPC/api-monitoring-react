import os
import secrets
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()

DASH_USER = os.environ["DASH_USER"]
DASH_PASS = os.environ["DASH_PASS"]


def require_basic_auth(credentials: HTTPBasicCredentials = Depends(security)):
    if not (secrets.compare_digest(credentials.username, DASH_USER) and
            secrets.compare_digest(credentials.password, DASH_PASS)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
