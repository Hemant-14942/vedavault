# app/services/auth.py

import traceback
from datetime import datetime
from uuid import uuid4
from typing import Dict, Any, Optional, Tuple

from fastapi import HTTPException, Request, Response

from app.config.db import users_collection, sessions_collection
from app.utils.security import (
    hash_password, 
    verify_password, 
    create_access_token, 
    create_refresh_token,
    verify_token,
    ACCESS_TOKEN_EXPIRY,
    REFRESH_TOKEN_EXPIRY
)


async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Get a user by email"""
    try:
        user = await users_collection.find_one({"email": email})
        if user:
            print(f"[INFO] get_user_by_email: Found user with email {email}")
        return user
    except Exception as e:
        print(f"[ERROR] get_user_by_email failed: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to fetch user")


async def register_user(name: str, email: str, password: str, response: Response, request: Request) -> Dict[str, Any]:
    """Register a new user"""
    try:
        existing_user = await get_user_by_email(email)
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")

        hashed_pw = hash_password(password)
        user = {
            "_id": str(uuid4()),
            "name": name,
            "email": email,
            "password": hashed_pw,
            "created_at": datetime.utcnow()
        }

        insert_result = await users_collection.insert_one(user)
        user["_id"] = str(insert_result.inserted_id)

        session_id = await create_session(user["_id"], request)
        await set_auth_cookies(user, session_id, response)

        user_response = dict(user)
        user_response.pop("password", None)

        print(f"[INFO] register_user: User registered with email {email}")
        return {"message": "register successful", "user": user_response}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] register_user failed: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="User registration failed")

async def create_session(user_id: str, request: Request) -> str:
    """Create a new session"""
    try:
        print("create_session krne ja raha hu byyy.....")
        # uuid4 generates a random UUID means for id it generate the random string 
        session_id = str(uuid4())
        session = {
            "_id": session_id,
            "user_id": user_id,
            "ip": request.client.host,
            "user_agent": request.headers.get("user-agent"),
            "valid": True,
            "created_at": datetime.utcnow(),
        }
        
        await sessions_collection.insert_one(session)
        print(f"[INFO] create_session: Session created for user_id {user_id}")
        return session_id
    
    except Exception as e:
        print(f"[ERROR] create_session failed: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to create session")


async def set_auth_cookies(user: Dict[str, Any], session_id: str, response: Response) -> None:
    """Set authentication cookies"""
    try:
        print("set_auth_cookies krne ja raha hu byyy.....")
        # Create tokens
        access_token = create_access_token(user, session_id)
        print(f"[INFO] set_auth_cookies: Access token created for session {session_id}")
        print(f"[INFO] set_auth_cookies: Access token: {access_token}")

        # session_id is passed to create_refresh_token function
        # to create the refresh token
        refresh_token = create_refresh_token(session_id)

        response.set_cookie(
            "access_token", 
            access_token, 
            max_age=ACCESS_TOKEN_EXPIRY, 
            httponly=True, 
            secure=True, 
            samesite="lax"
        )
        
        response.set_cookie(
            "refresh_token", 
            refresh_token, 
            max_age=REFRESH_TOKEN_EXPIRY, 
            httponly=True, 
            secure=True, 
            samesite="lax"
        )
        
        print(f"[INFO] set_auth_cookies: Tokens set for session {session_id}")
    
    except Exception as e:
        print(f"[ERROR] set_auth_cookies failed: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Authentication failed")


async def login_user(email: str, password: str, response: Response, request: Request) -> Dict[str, Any]:
    """Login a user"""
    try:
        print("login krne ja raha hu byyy.....")
        user = await get_user_by_email(email)
        if not user or not verify_password(password, user["password"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        session_id = await create_session(user["_id"], request)
        await set_auth_cookies(user, session_id, response)
        
        print(f"[INFO] login_user: Login successful for user {email}")
        
        # Remove password from response
        user_response = dict(user)
        user_response["_id"] = str(user_response["_id"])
        user_response["session_id"] = session_id
        user_response.pop("password", None)
        
        return {"message": "Login successful", "user": user_response}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] login_user failed: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Login failed")


async def refresh_tokens(refresh_token: str, response: Response) -> Tuple[Dict[str, Any], str, str]:
    """Refresh access and refresh tokens"""
    try:
        # Verify the refresh token
        payload = verify_token(refresh_token)
        session_id = payload.get("session_id")
        
        if not session_id:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        
        # Verify session
        session = await sessions_collection.find_one({"_id": session_id, "valid": True})
        if not session:
            raise HTTPException(status_code=401, detail="Session expired or invalid")
        
        # Get user data
        user = await users_collection.find_one({"_id": session["user_id"]})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Create new tokens
        new_access_token = create_access_token(user, session_id)
        new_refresh_token = create_refresh_token(session_id)
        
        # Update session with refresh timestamp
        await sessions_collection.update_one(
            {"_id": session_id},
            {"$set": {"last_refreshed": datetime.utcnow()}}
        )
        
        # Set new cookies
        response.set_cookie(
            "access_token", 
            new_access_token, 
            max_age=ACCESS_TOKEN_EXPIRY, 
            httponly=True, 
            secure=True,
            samesite="lax"
        )
        
        response.set_cookie(
            "refresh_token", 
            new_refresh_token, 
            max_age=REFRESH_TOKEN_EXPIRY, 
            httponly=True, 
            secure=True,
            samesite="lax"
        )
        
        # Remove password from response
        user_response = dict(user)
        user_response.pop("password", None)
        
        return user_response, new_access_token, new_refresh_token
    
    except Exception as e:
        print(f"[ERROR] refresh_tokens failed: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=401, detail="Failed to refresh tokens")


async def logout_user(session_id: str, response: Response) -> Dict[str, str]:
    """Logout a user"""
    try:
        print("logout krne ja raha hu byyy.....")
        # Invalidate session
        result = await sessions_collection.update_one(
            {"_id": session_id},
            {"$set": {"valid": False, "logged_out_at": datetime.utcnow()}}
        )
        #upper wala ye sbb bi return krega 
        print("\n--- Update Result Summary ---")
        print(f"Matched Documents   : {result.matched_count}")# Number of matched documents (0 or 1)
        print(f"Modified Documents  : {result.modified_count}")# Number of modified documents (0 or 1)
        print(f"Operation Acknowledged: {'✅ Yes' if result.acknowledged else '❌ No'}") # Usually True if the write concern was satisfied
        print("iske cokkies udata hua nikalo isko bhai.... 🙅‍♂️ ")
        # Clear cookies
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        
        return {"message": "Logout successful"}
    
    except Exception as e:
        print(f"[ERROR] logout_user failed: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Logout failed")