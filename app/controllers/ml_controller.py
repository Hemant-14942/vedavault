import os
import pandas as pd
from fastapi import UploadFile, Request, HTTPException
from fastapi.templating import Jinja2Templates
from typing import Dict, Any
from datetime import datetime
from uuid import uuid4
import traceback

# from app.modules.newmodelpipeline import EnhancedMLPipeline
from app.modules.model_pipeline import train_best_model
from app.services.ocr_services import extract_text_from_pdf, generate_insight_with_llm
from app.modules.insight_refiner import clean_and_structure, generate_questions
from app.modules.neweda import AutoEDAPipeline
from app.config.db import ml_collection

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"
templates = Jinja2Templates(directory="app/templates")

# 👋 NEW: Function to validate target column suitability based on task type
def validate_target_suitability(y: pd.Series, task_type: str):
    unique_classes = y.nunique()
    if task_type == "classification":
        if y.dtype.kind in "ifu":
            if unique_classes > 30:
                return False, "❌ Too many unique values for classification. Consider using regression."
        if unique_classes < 2:
            return False, "❌ Target column must have at least 2 classes for classification."
    elif task_type == "regression":
        if unique_classes < 10:
            return False, "❌ Too few unique values for regression. Consider using classification."
    return True, ""


async def upload_dataset(
    request: Request,
    file: UploadFile,
    task_type: str,
    target_col: str,
    pdf_file: UploadFile = None,
    current_user: Dict[str, Any] = None
):
    try:
        print("🔄 Received request to /upload")

        if not (file and task_type and target_col):
            raise HTTPException(status_code=400, detail="❌ Missing required fields.")

        user_id = current_user["_id"]
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        upload_id = f"{user_id}_{timestamp}"

        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        csv_filename = f"{upload_id}_{file.filename}"
        csv_filepath = os.path.join(UPLOAD_FOLDER, csv_filename)

        with open(csv_filepath, "wb") as f:
            f.write(await file.read())

        df = pd.read_csv(csv_filepath, encoding='utf-8', engine='python')
        df.columns = df.columns.str.strip().str.replace('\n', '', regex=True)
        df.columns = df.columns.str.encode('ascii', errors='ignore').str.decode('ascii')

        print("✅ Cleaned columns:", df.columns.tolist())

        target_col = target_col.strip()
        columns_map = {col.strip().lower(): col for col in df.columns}
        target_col_clean = target_col.lower()

        print(f"🔍 Cleaned target_col: {target_col_clean}")

        if target_col_clean not in columns_map:
            raise HTTPException(
                status_code=400,
                detail=f"❌ Target column '{target_col}' not found. Available: {list(df.columns)}"
            )

        target_col = columns_map[target_col_clean]
        print(f"✅ Matched actual column name: {target_col}")

        if target_col.lower() == 'price':
            df[target_col] = df[target_col].astype(str).str.replace(',', '')
            df[target_col] = df[target_col].replace({'Ask For Price': None})
            df[target_col] = pd.to_numeric(df[target_col], errors='coerce')

        # 👋 NEW: Target suitability check before proceeding
        is_valid, validation_msg = validate_target_suitability(df[target_col], task_type)
        if not is_valid:
            raise HTTPException(status_code=400, detail=validation_msg)

        # Run EDA
        print("🔍 Running EDA pipeline...")
        auto_eda = AutoEDAPipeline()
        clean_df, eda_summary = auto_eda.run_analysis(df, task_type=task_type, target_col=target_col)

        os.makedirs(OUTPUT_FOLDER, exist_ok=True)
        cleaned_filename = f"{upload_id}_cleaned.csv"
        clean_path = os.path.join(OUTPUT_FOLDER, cleaned_filename)
        clean_df.to_csv(clean_path, index=False)
        print("✅ Cleaned CSV saved.")

        # this is for clas based new modelpiple
        # Train model
        # print("🔍 Training best model...")
        # model_train = EnhancedMLPipeline()
        # report = model_train.train_and_evaluate(clean_df, task_type=task_type, target_col=target_col)
        
        #  Train model for old model pipeline
        print("🔍 Training best model...")
        best_model, report = train_best_model(clean_df, task_type=task_type)

        # Extract from EDA PDF if exists
        eda_pdf_path = os.path.join(OUTPUT_FOLDER, f"{upload_id}_eda_report.pdf")
        if os.path.exists(eda_pdf_path):
            eda_chart_text = extract_text_from_pdf(eda_pdf_path)
            eda_insight = generate_insight_with_llm(eda_chart_text, clean_df)
            report["EDA Chart Insight"] = clean_and_structure(eda_insight)
            report["EDA Suggested Questions"] = generate_questions(eda_insight)

        # Optional PowerBI PDF upload
        if pdf_file and pdf_file.filename:
            print("🔍 Processing Power BI PDF...")
            powerbi_filename = f"{upload_id}_powerbi_{pdf_file.filename}"
            powerbi_path = os.path.join(UPLOAD_FOLDER, powerbi_filename)
            with open(powerbi_path, "wb") as f:
                f.write(await pdf_file.read())

            powerbi_text = extract_text_from_pdf(powerbi_path)
            powerbi_insight = generate_insight_with_llm(powerbi_text, clean_df)
            report["Power BI Chart Insight"] = clean_and_structure(powerbi_insight)
            report["PowerBI Suggested Questions"] = generate_questions(powerbi_insight)
        else:
            print("⚠️ Power BI file not uploaded. Skipping PDF processing.")

        print("🔍 Returning response...")
        return templates.TemplateResponse("result.html", {"request": request, "report": report, "clean_path": clean_path})

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

        return {
            "status": "success",
            "message": "Upload and processing completed.",
            "cleaned_data_path": os.path.basename(clean_path),
            "eda_report_path": os.path.basename(eda_pdf_path),
            "report": report
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"❌ Internal error: {str(e)}")
