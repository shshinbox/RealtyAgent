from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
import jwt

from .deps import get_settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_current_user_id(
    token: str = Depends(oauth2_scheme),
    settings=Depends(get_settings),
) -> str:
    if not settings.SECRET_KEY:
        raise HTTPException(status_code=500, detail="SECRET_KEY missing")

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401)
        return user_id
    except jwt.PyJWTError:
        raise HTTPException(status_code=401)
