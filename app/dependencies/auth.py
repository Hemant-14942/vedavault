# app/dependencies/auth.py

from typing import Dict, Any, Optional
from fastapi import Depends, Request, Response, HTTPException
from fastapi.security import APIKeyCookie

from app.services.auth_services import refresh_tokens
from app.utils.security import verify_token
from app.config.db import sessions_collection

# Cookie extractors
access_cookie = APIKeyCookie(name="access_token", auto_error=False)
refresh_cookie = APIKeyCookie(name="refresh_token", auto_error=False)


async def verify_authentication(
    request: Request,
    response: Response,
    access_token: Optional[str] = Depends(access_cookie),
    refresh_token: Optional[str] = Depends(refresh_cookie)
) -> Optional[Dict[str, Any]]:
    """
    Verify authentication from cookies.
    Returns user data if authenticated, None otherwise.
    """
    # Default - not authenticated
    user = None
    
    # If no tokens, return None (not authenticated)
    if not access_token and not refresh_token:
        return None
    
    # Try access token first
    if access_token:
        try:
            # Decode the token
            payload = verify_token(access_token)
            
            # Verify session is still valid
            session_id = payload.get("session_id")
            if session_id:
                session = await sessions_collection.find_one({"_id": session_id, "valid": True})
                if not session:
                    # Session was invalidated, but we'll still try refresh token
                    raise HTTPException(status_code=401, detail="Session invalidated")
            
            # Return user info from token
            user = {
                "_id": payload.get("_id"),
                "email": payload.get("email"),
                "name": payload.get("name"),
                "session_id": session_id
            }
            return user
        except Exception:
            # Access token failed, try refresh token
            pass
    
    # Try refresh token if access token failed or is missing
    if refresh_token:
        try:
            # Get new tokens and user data
            user, _, _ = await refresh_tokens(refresh_token, response)
            return user
        except Exception:
            # Both tokens failed, return None (not authenticated)
            pass
    
    return user


async def require_authentication(
    current_user: Optional[Dict[str, Any]] = Depends(verify_authentication)
) -> Dict[str, Any]:
    """
    Requires authentication.
    Raises 401 if not authenticated.
    """
    if not current_user:
        raise HTTPException(
            status_code=401, 
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return current_user