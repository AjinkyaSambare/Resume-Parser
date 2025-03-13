import os
import uuid
from pathlib import Path
import PyPDF2
import docx
import pdfplumber
import fitz  # PyMuPDF

def save_uploaded_files(uploaded_files):
    """
    Save uploaded files to the uploads directory with unique filenames
    
    Args:
        uploaded_files: List of uploaded file objects from Streamlit
        
    Returns:
        List of paths to the saved files
    """
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
    """
    Extract raw text content from a file without preprocessing
    
    Args:
        file_path: Path to the file
        
    Returns:
        Raw extracted text content ready for Gemini processing
    """
    file_extension = Path(file_path).suffix.lower()
    
    try:
        if file_extension == ".pdf":
            raw_text = extract_text_from_pdf(file_path)
        elif file_extension == ".docx":
            raw_text = extract_text_from_docx(file_path)
        elif file_extension == ".txt":
            raw_text = extract_text_from_txt(file_path)
        else:
            return f"Unsupported file format: {file_extension}"
        
        return raw_text
    except Exception as e:
        print(f"Error extracting text from {file_path}: {e}")
        return ""

def extract_text_from_pdf(file_path):
    """
    Extract raw text from PDF using multiple methods for better reliability
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Extracted text content
    """
    text = ""

    # Try PyMuPDF first (usually most reliable)
    try:
        with fitz.open(file_path) as pdf:
            for page in pdf:
                text += page.get_text("text") + "\n"
        if text.strip():
            return text
    except Exception as e:
        print(f"PyMuPDF failed: {e}")

    # Fall back to pdfplumber if PyMuPDF fails
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n"
        if text.strip():
            return text
    except Exception as e:
        print(f"pdfplumber failed: {e}")

    # Last resort: PyPDF2
    try:
        with open(file_path, "rb") as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        print(f"PyPDF2 failed: {e}")

    return text.strip()

def extract_text_from_docx(file_path):
    """
    Extract raw text from DOCX file
    
    Args:
        file_path: Path to the DOCX file
        
    Returns:
        Extracted text content
    """
    try:
        doc = docx.Document(file_path)
        return "\n".join([p.text for p in doc.paragraphs])
    except Exception as e:
        print(f"Error reading DOCX file {file_path}: {e}")
        return ""

def extract_text_from_txt(file_path):
    """
    Extract raw text from TXT file
    
    Args:
        file_path: Path to the TXT file
        
    Returns:
        Extracted text content
    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
            return file.read()
    except Exception as e:
        print(f"Error reading TXT file {file_path}: {e}")
        return ""

def extract_name_from_file(file_path):
    """
    Try to extract a candidate name from file name
    
    Args:
        file_path: Path to the resume file
        
    Returns:
        Candidate name if it appears to be in the filename, otherwise None
    """
    filename = os.path.basename(file_path)
    filename = os.path.splitext(filename)[0]
    filename = filename.replace('_', ' ').replace('-', ' ')
    
    # If the filename has 2-3 words and only letters, it's likely a name
    words = filename.split()
    if 2 <= len(words) <= 3 and all(word.isalpha() for word in words):
        return ' '.join(words)
    
    return None