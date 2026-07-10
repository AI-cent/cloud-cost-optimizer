from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv
import os

load_dotenv()

_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
_DEFAULT_KEYS = {"", "fallback-secret-change-me", "changeme", "secret", "your-secret-key"}

if not _SECRET_KEY or _SECRET_KEY in _DEFAULT_KEYS:
    raise RuntimeError(
        "JWT_SECRET_KEY is missing or set to an insecure default. "
        "Set a strong random value in your .env file before starting the server."
    )

SECRET_KEY = _SECRET_KEY
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "24"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=EXPIRY_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
