# app/utils/security.py

import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple

from jose import jwt, JWTError
from passlib.context import CryptContext
from passlib.hash import argon2
from fastapi import HTTPException

# Security configuration
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key-for-development")
ALGORITHM = "HS256"

# Token expiration
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Cookie configuration
ACCESS_TOKEN_EXPIRY = ACCESS_TOKEN_EXPIRE_MINUTES * 60
REFRESH_TOKEN_EXPIRY = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60


def hash_password(password: str) -> str:
    """Hash a password using Argon2"""
    return argon2.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return argon2.verify(plain_password, hashed_password)


def create_access_token(user: Dict[str, Any], session_id: str) -> str:
    """Create an access token"""
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "_id": str(user["_id"]),
        "email": user["email"],
        "name": user["name"],
        "session_id": session_id,
        "exp": expire
    }
    
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(session_id: str) -> str:
    """Create a refresh token"""
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode = {
        "session_id": session_id,
        "exp": expire
    }
    
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> Dict[str, Any]:
    """Verify a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")