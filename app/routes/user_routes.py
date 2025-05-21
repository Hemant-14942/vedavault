# app/routers/auth.py

from fastapi import APIRouter, Depends, Response, Request
from typing import Dict, Any

from app.models.user import UserRegisterSchema, UserLoginSchema, TokenResponse, RegisterResponse
from app.services.auth_services import register_user, login_user, logout_user
from app.dependencies.auth import require_authentication

router = APIRouter()


@router.post("/register", response_model=RegisterResponse)
async def register(data: UserRegisterSchema, response: Response, request: Request):
    """Register a new user"""
    return await register_user(data.name, data.email, data.password, response, request)


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLoginSchema, response: Response, request: Request):
    """Login a user"""
    return await login_user(data.email, data.password, response, request)


@router.post("/logout", response_model=Dict[str, str])
async def logout(
    response: Response,
    current_user: Dict[str, Any] = Depends(require_authentication)
):
    """Logout a user"""
    return await logout_user(current_user["session_id"], response)


@router.get("/me", response_model=Dict[str, Any])
async def get_current_user(current_user: Dict[str, Any] = Depends(require_authentication)):
    """Get current authenticated user"""
    print(f"user ki info lene ja rah hu hauahaha spy bn gya m to sala..... 😅 ")
    return current_user