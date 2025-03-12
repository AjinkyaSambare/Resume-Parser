import os
import shutil
from pathlib import Path
import uuid
import PyPDF2
import docx
import pdfplumber
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from utils.preprocessor import preprocess_resume_text

def save_uploaded_files(uploaded_files):
    saved_paths = []
    upload_dir = Path("data/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    for uploaded_file in uploaded_files:
        file_extension = Path(uploaded_file.name).suffix
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = upload_dir / unique_filename
        
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        saved_paths.append(str(file_path))
    
    return saved_paths

def get_text_from_file(file_path):
    file_extension = Path(file_path).suffix.lower()
    
    try:
        if file_extension == ".pdf":
            raw_text = extract_text_from_pdf(file_path)
        elif file_extension == ".docx":
            raw_text = extract_text_from_docx(file_path)
        elif file_extension == ".txt":
            raw_text = extract_text_from_txt(file_path)
        elif file_extension in [".png", ".jpg", ".jpeg"]:
            raw_text = extract_text_from_image(file_path)
        else:
            return f"Unsupported file format: {file_extension}"
        
        preprocessed_text = preprocess_resume_text(raw_text)
        
        return preprocessed_text
    except Exception as e:
        print(f"Error extracting text from {file_path}: {e}")
        return ""

def extract_text_from_pdf(file_path):
    text = ""

    try:
        with fitz.open(file_path) as pdf:
            for page in pdf:
                text += page.get_text("text") + "\n"
        if text.strip():
            return text
    except Exception as e:
        print(f"PyMuPDF failed: {e}")

    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        print(f"pdfplumber failed: {e}")

    try:
        with open(file_path, "rb") as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        print(f"PyPDF2 failed: {e}")

    return text.strip()

def extract_text_from_docx(file_path):
    try:
        doc = docx.Document(file_path)
        return "\n".join([p.text for p in doc.paragraphs])
    except Exception as e:
        print(f"Error reading DOCX file {file_path}: {e}")
        return ""

def extract_text_from_txt(file_path):
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
            return file.read()
    except Exception as e:
        print(f"Error reading TXT file {file_path}: {e}")
        return ""

def extract_text_from_image(file_path):
    try:
        return pytesseract.image_to_string(Image.open(file_path))
    except Exception as e:
        print(f"OCR extraction failed for {file_path}: {e}")
        return ""