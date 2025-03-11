"""
Resume Preprocessor Module

This module handles preprocessing of resume text to normalize formatting
and make it easier for the AI to extract information correctly.
"""

import re
import os
from pathlib import Path


def preprocess_resume_text(text):
    """
    Preprocess resume text to normalize formatting before AI analysis
    
    Parameters:
    - text: Raw text extracted from the resume file
    
    Returns:
    - Preprocessed text with normalized formatting
    """
    if not text or len(text) < 50:
        return text
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Normalize asterisks formatting (commonly used for bold text in PDFs)
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    
    # Normalize bullet points
    text = re.sub(r'•|○|●|■|□|◆|◇|►|▶|★|☆|✓|✔|✗|✘', '- ', text)
    
    # Normalize section headers (convert to uppercase for consistency)
    section_headers = ['EDUCATION', 'EXPERIENCE', 'SKILLS', 'PROJECTS', 'ACHIEVEMENTS', 
                      'CERTIFICATIONS', 'LANGUAGES', 'PUBLICATIONS', 'INTERESTS']
    
    for header in section_headers:
        # Match variations like "education:", "Education", etc.
        pattern = re.compile(fr'({header}|{header.capitalize()}|{header.lower()})(\s*:)?', re.IGNORECASE)
        text = pattern.sub(f'## {header} ', text)
    
    # Process name separately - if it's formatted with asterisks or appears alone on a line
    name_match = re.search(r'^\s*(\w+\s+\w+(?:\s+\w+)?)\s*$', text, re.MULTILINE)
    if name_match:
        name = name_match.group(1)
        # Add a special marker for the name
        text = f"## NAME\n{name}\n" + text
    
    # Normalize newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text


def extract_name_from_file(file_path):
    """
    Try to extract candidate name from filename
    
    Parameters:
    - file_path: Path to the resume file
    
    Returns:
    - Candidate name if it can be extracted from filename, None otherwise
    """
    filename = os.path.basename(file_path)
    # Remove file extension
    filename = os.path.splitext(filename)[0]
    
    # Replace underscores and hyphens with spaces
    filename = filename.replace('_', ' ').replace('-', ' ')
    
    # Check if filename looks like a name (2-3 words, each capitalized)
    words = filename.split()
    if 2 <= len(words) <= 3 and all(word.isalpha() for word in words):
        return ' '.join(words)
    
    return None
