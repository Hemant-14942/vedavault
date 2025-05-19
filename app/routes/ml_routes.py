from fastapi import APIRouter, UploadFile, File, Form, Request

from app.controllers.ml_controller import upload_dataset
from starlette.responses import FileResponse
import os
router = APIRouter()

# Constants
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"
# Create directories if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


@router.post("/upload")
async def upload_dataset_route(
    request: Request,
    file: UploadFile = File(...),
    task_type: str = Form(...),
    target_col: str = Form(...),
    pdf_file: UploadFile = File(None)
):
    return await upload_dataset(request, file, task_type, target_col, pdf_file)

@router.get("/download")
async def download_cleaned_csv():
    file_path = os.path.join(OUTPUT_FOLDER, "cleaned_data.csv")
    return FileResponse(
        path=file_path,
        media_type="text/csv",
        filename="cleaned_data.csv"
    )
@router.get("/download_pdf")
async def download_pdf():
    return FileResponse(
        path="outputs/eda_report.pdf",
        media_type="application/pdf",
        filename="eda_report.pdf"
    )
