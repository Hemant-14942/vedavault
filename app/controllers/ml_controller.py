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
from app.services.ocr_services import generate_insight_with_llm
from app.modules.insight_refiner import clean_and_structure, generate_questions
from werkzeug.utils import secure_filename
from app.modules.neweda import AutoEDAPipeline

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

        df = pd.read_csv(filepath, encoding='utf-8', engine='python')
        # Clean column names
        df.columns = df.columns.str.strip().str.replace('\n', '', regex=True)
        df.columns = df.columns.str.encode('ascii', errors='ignore').str.decode('ascii')  # remove non-ascii characters
        print("✅ Cleaned columns:", df.columns.tolist())
        # print(df.columns)
        df = pd.read_csv(csv_filepath, encoding='utf-8', engine='python')
        df.columns = df.columns.str.strip()
        target_col = target_col.strip()
        print("------------------")
        print("--------**********---------")
        print("------------------")
        print(f"🔍 Raw target column (input): {target_col}")
        print("------------------")
        print("---------**************--------")
        print("------------------")

        # Normalize column names for safe comparison
        columns_map = {col.strip().lower(): col for col in df.columns}
        
        target_col_clean = target_col.lower()

        print(f"✅ Cleaned columns: {list(columns_map.keys())}")
        print(f"🔍 Cleaned target_col: {target_col_clean}")

        if target_col_clean not in columns_map:
            raise HTTPException(
                status_code=400,
                detail=f"❌ Target column '{target_col}' not found. Available: {list(df.columns)}"
            )

        # Use the actual column name from the dataset
        target_col = columns_map[target_col_clean]
        print(f"✅ Matched actual column name: {target_col}")

        # Handle price field if applicable
        if target_col.lower() == 'price':
            df[target_col] = df[target_col].astype(str).str.replace(
                ',', '').replace({'Ask For Price': None})
            df[target_col] = pd.to_numeric(df[target_col], errors='coerce')
            print(
                "🔍 before going to EDA everything is running. I am in ml_controller file.")

        # Run new EDA pipeline
        print("🔍 Running EDA pipeline...")
        auto_eda = AutoEDAPipeline()
        print("🔍 EDA pipeline ka instance bna liya abb run analysis call kr raha hu.")
        clean_df, eda_summary = auto_eda.run_analysis(
            df, task_type=task_type, target_col=target_col)
        os.makedirs(OUTPUT_FOLDER, exist_ok=True)
        cleaned_filename = f"{upload_id}_cleaned.csv"
        clean_path = os.path.join(OUTPUT_FOLDER, cleaned_filename)
        clean_df.to_csv(clean_path, index=False)
        print("🔍 EDA Summary:\n", eda_summary)

        # Train model
        best_model, report = train_best_model(clean_df, task_type=task_type)

        # Extract insight from EDA report
        eda_pdf_path = os.path.join(OUTPUT_FOLDER, f"{upload_id}_eda_report.pdf")
        if os.path.exists(eda_pdf_path):
            eda_chart_text = extract_text_from_pdf(eda_pdf_path)
            print("🔍 EDA Chart Text extracted.")
            eda_insight = generate_insight_with_llm(eda_chart_text, clean_df)
            print("🔍 EDA Chart Insight generated.")
            report["EDA Chart Insight"] = clean_and_structure(eda_insight)
            report["EDA Suggested Questions"] = generate_questions(eda_insight)
            print("🔍 EDA Chart questions added to report.")

        # Optional PDF from user (Power BI report)
        if pdf_file and pdf_file.filename:

            print("🔍 Power BI file uploaded.")
            pdf_path = os.path.join(
                UPLOAD_FOLDER, secure_filename(pdf_file.filename))
            pdf_file.save(pdf_path)
            powerbi_text = extract_text_from_pdf(pdf_path)
            print("🔍 Power BI Chart Text extracted.")

            print("🔍 Power BI file upload ho gaya")
            powerbi_filename = f"{upload_id}_powerbi_{pdf_file.filename}"
            powerbi_path = os.path.join(UPLOAD_FOLDER, powerbi_filename)
            with open(powerbi_path, "wb") as f:
                f.write(await pdf_file.read())
            powerbi_text = extract_text_from_pdf(powerbi_path)
            print("🔍 Power BI Chart Text nikla liya h")

            powerbi_insight = generate_insight_with_llm(powerbi_text, clean_df)
            report["Power BI Chart Insight"] = clean_and_structure(
                powerbi_insight)
            report["PowerBI Suggested Questions"] = generate_questions(
                powerbi_insight)
            print("🔍 Power BI questions added to report.")
        else:

            print("⚠️ Power BI file not uploaded. Skipping PDF processing.")

        print("🔍 Returning response...")
        return templates.TemplateResponse("result.html", {"request": request, "report": report, "clean_path": clean_path})


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
        raise HTTPException(
            status_code=500, detail=f"❌ Internal error: {str(e)}")
