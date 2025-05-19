# app/services/auth_service.py
from app.models.user import UserCreate, UserLogin, UserOut
from app.config.db import user_collection
from fastapi import HTTPException
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

import traceback

async def register_user(data: UserCreate):
    try:
        existing = await user_collection.find_one({"email": data.email})
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        hashed_password = pwd_context.hash(data.password)
        user_data = data.dict()
        user_data["password"] = hashed_password
        result = await user_collection.insert_one(user_data)
        # print("result checking===>",result)
        created = await user_collection.find_one({"_id": result.inserted_id})
        created["_id"] = str(created["_id"])  # Convert ObjectId to string
        return UserOut(**created)
    except Exception as e:
        print("Error during registration:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500,detail=str(e))

    
async def login_user(data: UserLogin):
    try:
        user = await user_collection.find_one({"email": data.email})
        if not user or "password" not in user or not pwd_context.verify(data.password, user["password"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        user.pop("password", None)  # remove password before returning
        user["_id"] = str(user["_id"])  # Convert ObjectId to str
        return {"message": "User login successfully", "user": UserOut(**user)}
    except Exception as e:
        print("Error during login:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
