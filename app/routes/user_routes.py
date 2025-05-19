# app/routes/auth.py
from fastapi import APIRouter
from app.models.user import UserCreate, UserLogin, UserOut, LoginResponse
from app.controllers.user_controller import register_user, login_user

router = APIRouter()

@router.post("/register", response_model=UserOut)
async def register(user: UserCreate):
    return await register_user(user)

@router.post("/login", response_model=LoginResponse)
async def login(user: UserLogin):
    return await login_user(user)
