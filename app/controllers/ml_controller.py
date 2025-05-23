import os
import pandas as pd
from werkzeug.utils import secure_filename
from fastapi import UploadFile, Request, HTTPException
from fastapi.templating import Jinja2Templates
from typing import Dict, Any
from datetime import datetime
from uuid import uuid4


from app.modules.eda_pipeline import auto_eda_pipeline
from app.modules.model_pipeline import train_best_model
from app.services.ocr_services import extract_text_from_pdf  # make sure this exists
from app.services.ocr_services import generate_insight_with_llm       # make sure this exists
from app.modules.insight_refiner import clean_and_structure, generate_questions
from app.config.db import sessions_collection,ml_collection

# from starlette.responses import FileResponse
import traceback

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"

templates = Jinja2Templates(directory="app/templates")


async def upload_dataset(request: Request, file: UploadFile, task_type: str, target_col: str, pdf_file: UploadFile = None, current_user: Dict[str, Any] = None):
    try:
        print("🔄 Received request to /upload")
        # Validate task type
        if not (file and task_type and target_col):
            return "❌ Missing required fields."
        user_id = current_user["_id"]
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        upload_id = f"{user_id}_{timestamp}"
        # Save the uploaded CSV
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        csv_filename = f"{upload_id}_{file.filename}"
        csv_filepath = os.path.join(UPLOAD_FOLDER, csv_filename)
        with open(csv_filepath, "wb") as f:
            f.write(await file.read())

        df = pd.read_csv(csv_filepath, encoding='utf-8', engine='python')
        df.columns = df.columns.str.strip()
        target_col = target_col.strip()

        if target_col not in df.columns:
            raise HTTPException(status_code=400, detail=f"❌ Target column '{target_col}' not found.")

        # Handle price field if applicable
        if target_col.lower() == 'price':
            df[target_col] = df[target_col].astype(str).str.replace(',', '').replace({'Ask For Price': None})
            df[target_col] = pd.to_numeric(df[target_col], errors='coerce')
            print("🔍 before goint to eda ervything running i am in ml_Conttroler file")

        clean_df, eda_summary = auto_eda_pipeline(df, task_type=task_type, target_col=target_col)
        os.makedirs(OUTPUT_FOLDER, exist_ok=True)
        cleaned_filename = f"{upload_id}_cleaned.csv"
        clean_path = os.path.join(OUTPUT_FOLDER, cleaned_filename)
        clean_df.to_csv(clean_path, index=False)

        print("🔍 EDA Summary:\n", eda_summary)

        best_model, report = train_best_model(clean_df, task_type=task_type)

        # Extract insight from EDA report
        eda_pdf_path = os.path.join(OUTPUT_FOLDER, f"{upload_id}_eda_report.pdf")
        if os.path.exists(eda_pdf_path):
            eda_chart_text = extract_text_from_pdf(eda_pdf_path)
            print("🔍 EDA Chart Text krne bbad aa chuka hu")
            eda_insight = generate_insight_with_llm(eda_chart_text, clean_df)
            print("🔍 EDA Chart Insight k baad hu m abhi:\n")
            report["EDA Chart Insight"] = clean_and_structure(eda_insight)
            print("🔍 EDA Chart Insight k baad report m daal diya:\n")
            report["EDA Suggested Questions"] = generate_questions(eda_insight)   #ye function insights modules kander h 
            print("🔍 EDA Chart Insight k baad question genrate krke  report m daal diya:\n")

        # Optional PDF from user (Power BI report)
        if pdf_file and pdf_file.filename:
            print("🔍 Power BI file upload ho gaya")
            powerbi_filename = f"{upload_id}_powerbi_{pdf_file.filename}"
            powerbi_path = os.path.join(UPLOAD_FOLDER, powerbi_filename)
            with open(powerbi_path, "wb") as f:
                f.write(await pdf_file.read())
            powerbi_text = extract_text_from_pdf(powerbi_path)
            print("🔍 Power BI Chart Text nikla liya h")
            powerbi_insight = generate_insight_with_llm(powerbi_text, clean_df)
            print("🔍 Power BI Chart Insight nikla liya h")
            report["Power BI Chart Insight"] = clean_and_structure(powerbi_insight)
            print("🔍 Power BI Chart Insight k baad report m daal diya:\n")
            report["PowerBI Suggested Questions"] = generate_questions(powerbi_insight)
            print("🔍 Power BI Chart Insight k baad question genrate krke  report m daal diya:\n")
        else:
            print("⚠️ Power BI file upload nahi hui. Skipping PDF processing.")
          # Save metadata in DB
        ml_data = await ml_collection.insert_one({
            "user_id": user_id,
            "upload_id": upload_id,
            "csv_path": csv_filepath,
            "eda_pdf_path": eda_pdf_path,
            "cleaned_path": clean_path,
            "created_at": datetime.utcnow(),
            "task_type": task_type,
            "target_column": target_col,
            "original_filename": file.filename
        })
        print("🔍 Metadata saved in DB with ID:", ml_data.inserted_id)
        print("✅ Upload and analysis completed.")

        # Return JSON instead of HTML (for React)
        return {
            "status": "success",
            "message": "Upload and processing completed.",
            "cleaned_data_path": os.path.basename(clean_path),
            "eda_report_path": os.path.basename(eda_pdf_path),
            "report": report
        }
        #  🚯 😦 frontend m esse use krna abb 
        #  <a href={`/download/${cleaned_data_path}`} download>Download Cleaned CSV</a>
        #  <a href={`/download_pdf/${eda_report_path}`} download>Download EDA PDF</a>
        # print("🔍bss abb return krne ja raha best of luck ni bologe ky 😲" )
        # return templates.TemplateResponse("result.html", {"request": request, "report": report, "clean_path": clean_path})
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"❌ Internal error: {str(e)}")
