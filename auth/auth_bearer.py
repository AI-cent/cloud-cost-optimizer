from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from auth.auth_handler import decode_token

security = HTTPBearer()


class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> str:
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(status_code=403, detail="Invalid authentication scheme.")
            payload = decode_token(credentials.credentials)
            if payload is None:
                raise HTTPException(status_code=401, detail="Token expired or invalid")
            return payload
        raise HTTPException(status_code=403, detail="Invalid authorization code.")


jwt_bearer = JWTBearer()
