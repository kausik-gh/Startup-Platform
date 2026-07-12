import os
import uuid
import jwt
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

security = HTTPBearer()


class RequestContext(BaseModel):
    user_id: Optional[uuid.UUID] = None  # Future domain user/person id
    auth_user_id: uuid.UUID
    email: str


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> RequestContext:
    token = credentials.credentials
    secret = os.getenv("SUPABASE_JWT_SECRET")

    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT secret not configured",
        )

    try:
        # Supabase JWTs use HS256 and their audience is typically "authenticated"
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"verify_aud": False},  # Or verify_aud=True, aud="authenticated"
        )

        auth_user_id_str = payload.get("sub")
        email = payload.get("email")

        if not auth_user_id_str or not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )

        return RequestContext(auth_user_id=uuid.UUID(auth_user_id_str), email=email)

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
