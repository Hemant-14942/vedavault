# controllers/chart_controller.py
import os
import shutil
from app.services.ocr_services import load_dataset
from app.services.ocr_services import ask_groq_about_chart
from app.services.ocr_services import extract_text_from_pdf  # make sure this exists
from app.services.ocr_services import generate_insight_with_llm   

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"

def process_uploaded_files(pdf_file, csv_file):
    print("🔍 Processing uploaded files...")
    if not (pdf_file and csv_file):
        raise ValueError("❌ Missing required files.")
    pdf_path = os.path.join(UPLOAD_FOLDER, pdf_file.filename)
    csv_path = os.path.join(UPLOAD_FOLDER, csv_file.filename)

    with open(pdf_path, "wb") as f:
        shutil.copyfileobj(pdf_file.file, f)
    with open(csv_path, "wb") as f:
        shutil.copyfileobj(csv_file.file, f)
    print("🔍 Files saved successfully.")
    print("abb m chart wale m text extract krne ki aur ja rah ahu");

    chart_text = extract_text_from_pdf(pdf_path)
    print("🔍 Chart text extracted successfully.")
    df = load_dataset(csv_path)
    insight = generate_insight_with_llm(chart_text, df)
    print("🔍 Insight generated successfully. m chart k ander hu hahaaha...")
    return insight

def generate_response_from_question(question, context):
    return ask_groq_about_chart(question, context)

def write_chat_to_file(chat):
    file_path = os.path.join(OUTPUT_FOLDER, "chat_history.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("🧠 InsightForge.AI - Chat Q&A History\n\n")
        for q, a in chat:
            f.write(f"Q: {q}\nA: {a}\n\n")
    return file_path
