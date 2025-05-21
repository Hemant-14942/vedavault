from fastapi import FastAPI, File, UploadFile, Form, HTTPException,APIRouter
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import os

# for adding templates html files
from starlette.responses import FileResponse
from starlette.middleware.sessions import SessionMiddleware

from app.config.db import test_connection
from app.routes.user_routes import router as user_router
from app.routes.ml_routes import router as ml_router
from app.routes.chart_routes import router as chart_router
from app.utils.cleanup import register_cleanup_task


app = FastAPI()
router = APIRouter()
app.add_middleware(SessionMiddleware, secret_key="hemant123")

# Configure CORS
origins = [
    "http://localhost:3000",  # React frontend
    "http://localhost:8000",  # Development
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# Templates setup
templates = Jinja2Templates(directory="app/templates")
# Serve static files (like in Flask)
app.mount("/static", StaticFiles(directory="static"), name="static")




@app.on_event("startup")
async def startup_db_check():
    await test_connection()

app.include_router(user_router, prefix="/users", tags=["Users"])
# app.include_router(ml_router, prefix="/ml", tags=["ML"])
app.include_router(ml_router,tags=["ML"])
app.include_router(chart_router,tags=["Chart"])

# for cleaning up the sessions which ar eof no use
register_cleanup_task(app) 

@app.get("/")
async def read_index():
     return templates.TemplateResponse("index.html", {"request": {}})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)




