from fastapi import APIRouter, UploadFile, File, Form, Request,Depends,HTTPException
from starlette.responses import FileResponse
import os
from typing import Dict, Any



from app.controllers.ml_controller import upload_dataset
from app.dependencies.auth import require_authentication

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
    current_user: Dict[str, Any] = Depends(require_authentication),
    file: UploadFile = File(...),
    task_type: str = Form(...),
    target_col: str = Form(...),
    pdf_file: UploadFile = File(None)
):
    return await upload_dataset(request, file, task_type, target_col, pdf_file,current_user)



  #  🚯 😦 frontend m esse use krna abb 
        #  <a href={`/download/${cleaned_data_path}`} download>Download Cleaned CSV</a>
        #  <a href={`/download_pdf/${eda_report_path}`} download>Download EDA PDF</a>

@router.get("/download/{filename}")
async def download_cleaned_csv(
    filename: str,
    current_user: Dict[str, Any] = Depends(require_authentication)
):
    file_path = os.path.join(OUTPUT_FOLDER, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found.")

    # Optional: Ensure filename includes user_id to restrict access
    if not filename.startswith(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Access denied: This file does not belong to you.")

    return FileResponse(
        path=file_path,
        media_type="text/csv",
        filename=filename
    )

@router.get("/download_pdf/{filename}")
async def download_pdf(
    filename: str,
    current_user: Dict[str, Any] = Depends(require_authentication)
):
    file_path = os.path.join(OUTPUT_FOLDER, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found.")

    # Optional: Ensure filename includes user_id to restrict access
    if not filename.startswith(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Access denied: This file does not belong to you.")

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=filename
    )
