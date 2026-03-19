from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from ..deps import get_settings

router = APIRouter()


@router.post("/token")
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    settings=Depends(get_settings),
):
    if not settings.SECRET_KEY:
        raise HTTPException(status_code=500, detail="SECRET_KEY missing")

    if (
        form.username != settings.AUTH_USERNAME
        or form.password != settings.AUTH_PASSWORD
    ):
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 틀렸습니다.")

    payload = {
        "user_id": form.username,
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    return {"access_token": token, "token_type": "bearer"}
