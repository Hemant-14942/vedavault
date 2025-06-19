# app/database.py
import motor.motor_asyncio
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME")

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = client[DATABASE_NAME]

# Collections

users_collection = db["users"]
ml_collection = db["ml_records"]
chart_insights_collection = db["chart_insights"]


sessions_collection = db["sessions"]  # Assuming you have a sessions collection

async def test_connection():
    try:
        info = await client.server_info()
        print("✅ MongoDB connected:", info["version"])
    except Exception as e:
        print("❌ MongoDB connection failed:", e)
# If session_id is UUID string instead of ObjectId
async def get_session_by_id(session_id: str):
    session = await sessions_collection.find_one({"_id": session_id})
    return session


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_connection())
