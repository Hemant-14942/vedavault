# app/database.py
import motor.motor_asyncio
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME")

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
database = client[DATABASE_NAME]

# Collections
student_collection = database["students"]
user_collection = database["users"]  # just as example

async def test_connection():
    try:
        info = await client.server_info()
        print("✅ MongoDB connected:", info["version"])
    except Exception as e:
        print("❌ MongoDB connection failed:", e)

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_connection())
