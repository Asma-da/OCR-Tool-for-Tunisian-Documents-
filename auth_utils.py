# auth_utils.py
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt, JWTError
from fastapi import HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import hashlib

from database import get_collection
from bson import ObjectId
from config import Config

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)

# ------------------------
# Password hashing (SHA256 + bcrypt)
# ------------------------
def hash_password(password: str) -> str:
    # Pre-hash with SHA256 to avoid bcrypt 72-byte limit
    sha = hashlib.sha256(password.encode()).hexdigest()
    return pwd_context.hash(sha)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    sha = hashlib.sha256(plain_password.encode()).hexdigest()
    return pwd_context.verify(sha, hashed_password)

# ------------------------
# JWT token creation
# ------------------------
def create_access_token(data: dict, expires_minutes: int = Config.ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, Config.SECRET_KEY, algorithm=Config.ALGORITHM)
    return token

# ------------------------
# JWT verification from cookie or header
# ------------------------
def get_current_user(
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = None
):
    token = None

    # Try to get token from cookie first
    cookie_token = request.cookies.get("access_token")
    if cookie_token and cookie_token.startswith("Bearer "):
        token = cookie_token.replace("Bearer ", "")

    # If no cookie, try Authorization header
    elif credentials:
        token = credentials.credentials

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=[Config.ALGORITHM])
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

    users_col = get_collection("users")
    user = users_col.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Convert ObjectId to string for easier handling
    user["_id"] = str(user["_id"])
    return user
