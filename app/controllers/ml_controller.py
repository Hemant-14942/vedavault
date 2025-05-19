import os
import pandas as pd
from fastapi import UploadFile, Request, HTTPException
from fastapi.templating import Jinja2Templates
from app.modules.eda_pipeline import auto_eda_pipeline
from app.modules.model_pipeline import train_best_model
from app.services.ocr_services import extract_text_from_pdf  # make sure this exists
from app.services.ocr_services import generate_insight_with_llm       # make sure this exists
from app.modules.insight_refiner import clean_and_structure, generate_questions
from werkzeug.utils import secure_filename
# from starlette.responses import FileResponse
import traceback

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"

templates = Jinja2Templates(directory="app/templates")


async def upload_dataset(request: Request, file: UploadFile, task_type: str, target_col: str, pdf_file: UploadFile = None):
    try:
        # Validate task type
        if not (file and task_type and target_col):
            return "❌ Missing required fields."
        # Save the uploaded CSV
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        with open(filepath, "wb") as f:
            f.write(await file.read())

        df = pd.read_csv(filepath, encoding='utf-8', engine='python')
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
        clean_path = os.path.join(OUTPUT_FOLDER, "cleaned_data.csv")
        clean_df.to_csv(clean_path, index=False)

        print("🔍 EDA Summary:\n", eda_summary)

        best_model, report = train_best_model(clean_df, task_type=task_type)

        # Extract insight from EDA report
        eda_pdf_path = "outputs/eda_report.pdf"
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
            pdf_path = os.path.join(UPLOAD_FOLDER, secure_filename(pdf_file.filename))
            pdf_file.save(pdf_path)
            powerbi_text = extract_text_from_pdf(pdf_path)
            print("🔍 Power BI Chart Text nikla liya h")
            powerbi_insight = generate_insight_with_llm(powerbi_text, clean_df)
            print("🔍 Power BI Chart Insight nikla liya h")
            report["Power BI Chart Insight"] = clean_and_structure(powerbi_insight)
            print("🔍 Power BI Chart Insight k baad report m daal diya:\n")
            report["PowerBI Suggested Questions"] = generate_questions(powerbi_insight)
            print("🔍 Power BI Chart Insight k baad question genrate krke  report m daal diya:\n")
        else:
            print("⚠️ Power BI file upload nahi hui. Skipping PDF processing.")

        # # Return JSON instead of HTML (for React)
        # return {
        #     "status": "success",
        #     "message": "Upload and processing completed.",
        #     "cleaned_data_path": clean_path,
        #     "eda_report_path": eda_pdf_path,
        #     "report": report
        # }
        print("🔍bss abb return krne ja raha best of luck ni bologe ky 😲" )
        return templates.TemplateResponse("result.html", {"request": request, "report": report, "clean_path": clean_path})
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"❌ Internal error: {str(e)}")
