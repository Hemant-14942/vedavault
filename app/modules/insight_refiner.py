# modules/insight_refiner.py

import re
import spacy
import random
import traceback


import spacy
import traceback

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("🔄 'en_core_web_sm' not found. Attempting to download it...")
    from spacy.cli import download
    download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")
except Exception:
    print("❌ Unexpected error while loading spaCy model:")
    print(traceback.format_exc())
    raise RuntimeError("Could not load spaCy model 'en_core_web_sm'")


TEMPLATES = [
    "How does {X} impact {Y}?",
    "What policies could improve {Y} considering {X}?",
    "Why might {X} be affecting {Y}?",
    "What can be inferred from the relationship between {X} and {Y}?",
    "How can we reduce or increase {Y} by changing {X}?"
]

def extract_entities(text):
    try:
        doc = nlp(text)
        chunks = list(set([chunk.text.strip() for chunk in doc.noun_chunks if len(chunk.text.strip()) > 2]))
        return chunks
    except Exception as e:
        error_trace = traceback.format_exc()
        print("⚠️ Error in extract_entities:")
        print(error_trace)
        return []

def generate_questions(text):
    try:
        entities = extract_entities(text)
        if len(entities) < 2:
            return ["What are the implications of this insight?"]

        questions = []
        for _ in range(min(3, len(entities))):
            X, Y = random.sample(entities, 2)
            template = random.choice(TEMPLATES)
            questions.append(template.format(X=X, Y=Y))
        return questions

    except Exception as e:
        error_trace = traceback.format_exc()
        print("⚠️ Error in generate_questions:")
        print(error_trace)
        return ["What are the implications of this insight?"]

def clean_and_structure(insight_block):
    try:
        # Clean Markdown or bold markers
        cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", insight_block).strip()
        return cleaned
    except Exception as e:
        error_trace = traceback.format_exc()
        print("⚠️ Error in clean_and_structure:")
        print(error_trace)
        return insight_block  # Return original if cleaning fails
