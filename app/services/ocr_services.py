import cv2
from pdf2image import convert_from_bytes
import pytesseract
import numpy as np
import pandas as pd
import requests

GROQ_API_KEY = "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"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama3-8b-8192"
pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
SECRET_KEY = 'your_secret_key_here'
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"



def extract_chart_regions(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cropped = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if w > 200 and h > 150:
            chart_img = image[y:y + h, x:x + w]
            cropped.append(chart_img)
            cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)
    cv2.imwrite("static/charts/ocr_overlay.png", image)
    return cropped

def ocr_chart(img):
    print("🔍 Performing OCR on chart...")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return pytesseract.image_to_string(gray)

def extract_text_from_pdf(file_path):
    print("🔍 Extracting text from PDF...")
    with open(file_path, 'rb') as f:
        images = convert_from_bytes(f.read())
    full_text = ''
    for page in images:
        np_img = np.array(page)
        cropped_charts = extract_chart_regions(np_img)
        for chart_img in cropped_charts:
            full_text += ocr_chart(chart_img) + "\n"
    print("🔍 Extracted Chart Text:\n", full_text)
    return full_text

def load_dataset(csv_path):
    try:
        return pd.read_csv(csv_path)
    except:
        return None

def generate_insight_with_llm(chart_text, df):
    print("🔍 Generating insights with LLM...")
    df_preview = df.head(10).to_string() if df is not None else "No dataset available."
    prompt = f"""
You are a data analyst AI. Here is some text extracted from chart regions in a dashboard:

--- Chart Text ---
{chart_text}

--- CSV Dataset Preview ---
{df_preview}

Please generate 3-5 meaningful business insights based on trends shown in the charts.
"""
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.5
    }
    response = requests.post(GROQ_API_URL, headers=headers, json=payload)
    return response.json()['choices'][0]['message']['content'] if response.status_code == 200 else f"Error: {response.text}"

def ask_groq_about_chart(question, context):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    prompt = f"Context: {context}\n\nUser: {question}"
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.5
    }
    response = requests.post(GROQ_API_URL, headers=headers, json=payload)
    return response.json()['choices'][0]['message']['content'] if response.status_code == 200 else f"Error: {response.text}"
