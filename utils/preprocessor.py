import re
import os
from pathlib import Path

def preprocess_resume_text(text):
    if not text or len(text) < 50:
        return text
    
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    text = re.sub(r'•|○|●|■|□|◆|◇|►|▶|★|☆|✓|✔|✗|✘', '- ', text)
    
    section_headers = ['EDUCATION', 'EXPERIENCE', 'SKILLS', 'PROJECTS', 'ACHIEVEMENTS', 
                      'CERTIFICATIONS', 'LANGUAGES', 'PUBLICATIONS', 'INTERESTS']
    
    for header in section_headers:
        pattern = re.compile(fr'({header}|{header.capitalize()}|{header.lower()})(\s*:)?', re.IGNORECASE)
        text = pattern.sub(f'## {header} ', text)
    
    name_match = re.search(r'^\s*(\w+\s+\w+(?:\s+\w+)?)\s*$', text, re.MULTILINE)
    if name_match:
        name = name_match.group(1)
        text = f"## NAME\n{name}\n" + text
    
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text

def extract_name_from_file(file_path):
    filename = os.path.basename(file_path)
    filename = os.path.splitext(filename)[0]
    filename = filename.replace('_', ' ').replace('-', ' ')
    
    words = filename.split()
    if 2 <= len(words) <= 3 and all(word.isalpha() for word in words):
        return ' '.join(words)
    
    return None