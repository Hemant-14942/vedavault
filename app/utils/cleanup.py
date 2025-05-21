from datetime import datetime, timedelta
from fastapi_utils.tasks import repeat_every
from fastapi import FastAPI
from app.config.db import sessions_collection  # adjust path to your collection

def register_cleanup_task(app: FastAPI):
    @app.on_event("startup")
    @repeat_every(seconds=60 * 60 * 24)  # Run once every 24 hours
    async def cleanup_old_sessions():
        threshold = datetime.utcnow() - timedelta(days=30)
        result = await sessions_collection.delete_many({
            "valid": False,
            "logged_out_at": {"$lt": threshold}
        })
        print(f"[CLEANUP] ✅ Deleted {result.deleted_count} old invalid sessions.")