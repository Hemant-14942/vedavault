# chart_routes.py
from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from app.dependencies.auth import require_authentication
from app.config.db import chart_insights_collection
from app.services.ocr_services import extract_text_from_pdf, generate_insight_with_llm, load_dataset
from app.controllers.chart_controller import (
    process_uploaded_files,
    generate_response_from_question,
    write_chat_to_file
)

import os
import shutil
import traceback
from datetime import datetime
from uuid import uuid4

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"
templates = Jinja2Templates(directory="app/templates")

router = APIRouter()

@router.api_route("/chart-talk", methods=["GET", "POST"])
async def chart_talk(
    request: Request,
    pdf_file: UploadFile = File(None),
    csv_file: UploadFile = File(None),
    question: str = Form(None),
    current_user: dict = Depends(require_authentication)
):
    session = request.session
    print("🔄 Received request to /chart-talk")

    if 'chat_history' not in session:
        print("💬 chat_history not in session — initializing...")
        session['chat_history'] = []

    try:
        if request.method == "POST":
            print("📡 POST request received")

            if pdf_file and csv_file and pdf_file.filename and csv_file.filename:
                print(f"📄 PDF uploaded: {pdf_file.filename}")
                print(f"📊 CSV uploaded: {csv_file.filename}")

                timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
                user_id = current_user["_id"]
                unique_prefix = f"{user_id}_{timestamp}"

                os.makedirs(UPLOAD_FOLDER, exist_ok=True)

                pdf_filename = f"{unique_prefix}_{pdf_file.filename}"
                csv_filename = f"{unique_prefix}_{csv_file.filename}"

                pdf_path = os.path.join(UPLOAD_FOLDER, pdf_filename)
                csv_path = os.path.join(UPLOAD_FOLDER, csv_filename)

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

                insight_id = str(uuid4())
                session['insight'] = insight
                session['chat_history'] = []
                session['insight_id'] = insight_id

                # Save to MongoDB
                await chart_insights_collection.insert_one({
                    "user_id": user_id,
                    "insight_id": insight_id,
                    "created_at": datetime.utcnow(),
                    "pdf_path": pdf_path,
                    "csv_path": csv_path,
                    "insight": insight,
                    "chat_history": []
                })

            elif question:
                print(f"❓ Received question: {question}")
                context = session.get("insight", "")
                reply = generate_response_from_question(question, context)
                print(f"💡 Generated reply: {reply}")

                chat_entry = {"question": question, "answer": reply}
                session['chat_history'].append(chat_entry)
                insight_id = session.get("insight_id")
                if insight_id:
                    await chart_insights_collection.update_one(
                        {"user_id": current_user["_id"], "insight_id": insight_id},
                        {"$push": {"chat_history": chat_entry}}
                    )

            else:
                print("⚠️ POST request missing both files and question")

    except Exception as e:
        error_trace = traceback.format_exc()
        print("❌ Exception occurred in /chart-talk POST:")
        print(error_trace)

        return {
        "status": "error",
        "message": f"❌ An error occurred: {str(e)}",
        "traceback": error_trace
    }

    print("📤 Rendering chart_talk.html page.")
    return {
        "status": "success",
        "insight": session.get("insight", ""),
        "chat_history": session.get("chat_history", []),
        "insight_id": session.get("insight_id")
    }


@router.post("/ask-question")
async def ask_question(
    request: Request,
    question: str = Form(...),
    context: str = Form(""),
    current_user: dict = Depends(require_authentication)
):
    try:
        print(f"[ASK] Received question: {question}")
        print(f"[ASK] Context: {context[:100]}...")

        reply = generate_response_from_question(question, context)
        print(f"[ASK] Generated reply: {reply}")

        session = request.session
        if 'chat_history' not in session:
            print("[ASK] Initializing empty chat_history in session.")
            session['chat_history'] = []

        session['chat_history'].append((question, reply))

        insight_id = session.get("insight_id")
        if insight_id:
            await chart_insights_collection.update_one(
                {"user_id": current_user["_id"], "insight_id": insight_id},
                {"$push": {"chat_history": (question, reply)}}
            )

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
    
#     -----------------------------👌 ---------------------------------
# esse use krna frontend me 
# const res = await axios.post("/chart-talk", formData);
# const insightId = res.data.insight_id;
# <a href={`/download_chat/${insightId}`} download>Download Chat History</a>
#     -----------------------------👌 ---------------------------------
@router.get("/download_chat/{insight_id}")
async def download_chat(insight_id: str, current_user: dict = Depends(require_authentication)):
    try:
        print("[DOWNLOAD] Request to download chat history received.")

        from app.config.db import chart_insights_collection

        insight = await chart_insights_collection.find_one({
            "user_id": current_user["_id"],
            "insight_id": insight_id
        })

        if not insight or "chat_history" not in insight:
            print("[DOWNLOAD] No chat history found in DB.")
            raise HTTPException(status_code=400, detail="No chat history found.")

        chat = insight["chat_history"]
        print(f"[DOWNLOAD] Retrieved chat history from session: {len(chat)} messages")

        if not chat:
            print("[DOWNLOAD] No chat history found in session.")
            raise HTTPException(status_code=400, detail="No chat history found.")

        filename = f"{current_user['_id']}_{insight_id}_chat_history.txt"
        file_path = write_chat_to_file(chat, filename)
        return FileResponse(file_path, filename=filename, media_type="text/plain")

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print("⚠️ Error in /download_chat route:")
        print(error_trace)

        return {
            "error": f"❌ An error occurred: {str(e)}",
            "traceback": error_trace
        }
