# chart_routes.py
from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
import os
import shutil
import traceback
from app.services.ocr_services import extract_text_from_pdf  
from app.services.ocr_services import generate_insight_with_llm 
from app.services.ocr_services import load_dataset

from app.controllers.chart_controller import (
    process_uploaded_files,
    generate_response_from_question,
    write_chat_to_file
)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"
templates = Jinja2Templates(directory="app/templates")

router = APIRouter()


@router.api_route("/chart-talk", methods=["GET", "POST"])
async def chart_talk(request: Request,
                     pdf_file: UploadFile = File(None),
                     csv_file: UploadFile = File(None),
                     question: str = Form(None)):
    session = request.session
    print("🔄 Received request to /chart-talk")

    if 'chat_history' not in session:
        print("💬 chat_history not in session — initializing...")
        session['chat_history'] = []
        # session.modified = True

    try:
        if request.method == "POST":
            print("📡 POST request received")
            
            if pdf_file and csv_file and pdf_file.filename and csv_file.filename:
                print(f"📄 PDF uploaded: {pdf_file.filename}")
                print(f"📊 CSV uploaded: {csv_file.filename}")

                os.makedirs(UPLOAD_FOLDER, exist_ok=True)

                pdf_path = os.path.join(UPLOAD_FOLDER, pdf_file.filename)
                csv_path = os.path.join(UPLOAD_FOLDER, csv_file.filename)

                print(f"💾 Saving PDF to: {pdf_path}")
                with open(pdf_path, "wb") as f:
                    shutil.copyfileobj(pdf_file.file, f)

                print(f"💾 Saving CSV to: {csv_path}")
                with open(csv_path, "wb") as f:
                    shutil.copyfileobj(csv_file.file, f)

                print("🔍 Extracting text from PDF...")
                chart_text = extract_text_from_pdf(pdf_path)
                print("✅ Extracted chart text.")

                print("📥 Loading dataset from CSV...")
                df = load_dataset(csv_path)
                print("✅ CSV loaded into DataFrame.")

                print("🧠 Generating insight from chart text and data...")
                insight = generate_insight_with_llm(chart_text, df)
                print("✅ Insight generated.")

                session['insight'] = insight
                # request.session["context"] = insight
                session['chat_history'] = []
                print("💾 Insight and chat history saved in session.")

            elif question:
                print(f"❓ Received question: {question}")
                context = session.get("insight", "")
                reply = generate_response_from_question(question, context)
                print(f"💡 Generated reply: {reply}")

                session['chat_history'].append((question, reply))
                print("💬 Chat history updated with new Q&A.")

            else:
                print("⚠️ POST request missing both files and question")

    except Exception as e:
        error_trace = traceback.format_exc()
        print("❌ Exception occurred in /chart-talk POST:")
        print(error_trace)

        return templates.TemplateResponse("chart_talk.html", {
            "request": request,
            "insight": f"❌ An error occurred:\n{str(e)}\n\nTraceback:\n{error_trace}",
            "chat_history": session.get("chat_history", [])
        })

    print("📤 Rendering chart_talk.html page.")
    return templates.TemplateResponse("chart_talk.html", {
        "request": request,
        "insight": session.get("insight", ""),
        "chat_history": session.get("chat_history", [])
    })

@router.post("/ask-question")
async def ask_question(request: Request, question: str = Form(...), context: str = Form("")):
    try:
        print(f"[ASK] Received question: {question}")
        # context = request.session.get("context", "")
        print(f"[ASK] Context: {context[:100]}...")  # Print first 100 chars for brevity

        reply = generate_response_from_question(question, context)
        print(f"[ASK] Generated reply: {reply}")

        session = request.session
        if 'chat_history' not in session:
            print("[ASK] Initializing empty chat_history in session.")
            session['chat_history'] = []

        session['chat_history'].append((question, reply))
        # session.modified = True
        print("[ASK] Updated session chat_history.")

        return {"answer": reply}

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print("⚠️ Error in ask-question route:")
        print(error_trace)
        return {
            "answer": f"❌ Error occurred: {str(e)}",
            "traceback": error_trace
        }

@router.get("/download_chat")
async def download_chat(request: Request):
    try:
        print("[DOWNLOAD] Request to download chat history received.")

        chat = request.session.get("chat_history", [])
        print(f"[DOWNLOAD] Retrieved chat history from session: {len(chat)} messages")

        if not chat:
            print("[DOWNLOAD] No chat history found in session.")
            raise HTTPException(status_code=400, detail="No chat history found.")

        file_path = write_chat_to_file(chat)
        print(f"[DOWNLOAD] Chat written to file: {file_path}")

        return FileResponse(file_path, filename="chat_history.txt", media_type="text/plain")

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print("⚠️ Error in /download_chat route:")
        print(error_trace)

        return {
            "error": f"❌ An error occurred: {str(e)}",
            "traceback": error_trace
        }
