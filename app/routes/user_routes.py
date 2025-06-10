# app/routers/auth.py

from fastapi import APIRouter, Depends, Response, Request, Form
from typing import Dict, Any
from pydantic import EmailStr


from app.models.user import  TokenResponse, RegisterResponse
from app.services.auth_services import register_user, login_user, logout_user
from app.dependencies.auth import require_authentication

router = APIRouter()


@router.post("/register", response_model=RegisterResponse)
async def register(
    response: Response,
    request: Request,
    name: str = Form(...),
    email: EmailStr = Form(...),
    password: str = Form(...),
):
    """Register a new user"""
    return await register_user(name, email, password, response, request)


@router.post("/login", response_model=TokenResponse)
async def login(
    response: Response,
    request: Request,
    email: EmailStr = Form(...),
    password: str = Form(...), 
):

    """Login a user"""
    return await login_user(email, password, response, request)


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