"""
Google Gemini processor for Resume Parser application.
This module handles communication with Google's Generative AI API.
"""

import os
import json
import time
import random
import threading
from queue import Queue
import concurrent.futures
from pathlib import Path
from utils.file_handler import get_text_from_file

# Check if Google Generative AI is available
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("Google Generative AI package not available. Install it using: pip install google-generativeai")

class RateLimiter:
    """
    Implements rate limiting for API calls with adaptive backoff
    """
    def __init__(self, initial_delay=1, max_delay=60, backoff_factor=1.5):
        self.current_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.last_request_time = 0
        self.lock = threading.Lock()
    
    def wait(self):
        """Wait the appropriate amount of time before next request"""
        with self.lock:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.current_delay:
                time.sleep(self.current_delay - elapsed)
            self.last_request_time = time.time()
    
    def success(self):
        """Call after successful request to gradually decrease wait time"""
        with self.lock:
            # Gradually decrease delay after successful calls, but not below initial
            self.current_delay = max(self.current_delay / 1.2, 1)
    
    def failure(self):
        """Call after rate limit failure to increase wait time"""
        with self.lock:
            # Increase delay with some randomness to avoid synchronized retries
            jitter = random.uniform(0.8, 1.2)
            self.current_delay = min(self.current_delay * self.backoff_factor * jitter, self.max_delay)
            return self.current_delay

class ProcessingQueue:
    """
    Manages a queue of resume processing tasks with rate limiting
    """
    def __init__(self, processor):
        self.processor = processor
        self.queue = Queue()
        self.results = {}
        self.processing = False
        self.worker_thread = None
        self.lock = threading.Lock()
    
    def add_task(self, file_path, user_filters=None, callback=None):
        """Add a resume processing task to the queue"""
        task_id = str(Path(file_path).stem)
        self.queue.put((task_id, file_path, user_filters))
        self.results[task_id] = {"status": "queued", "data": None, "error": None}
        
        # Start processing if not already running
        if not self.processing:
            self.start_processing()
        
        return task_id
    
    def start_processing(self):
        """Start the background processing thread"""
        if not self.processing:
            self.processing = True
            self.worker_thread = threading.Thread(target=self._process_queue)
            self.worker_thread.daemon = True
            self.worker_thread.start()
    
    def _process_queue(self):
        """Process queue items one by one with rate limiting"""
        while not self.queue.empty():
            # Get the next task
            task_id, file_path, user_filters = self.queue.get()
            
            # Update status to processing
            with self.lock:
                self.results[task_id]["status"] = "processing"
            
            try:
                # Process the resume
                if user_filters:
                    result = self.processor.analyze_document_with_filters(file_path, user_filters)
                else:
                    result = self.processor.analyze_document(file_path)
                
                # Store the result
                with self.lock:
                    self.results[task_id] = {
                        "status": "completed",
                        "data": result,
                        "error": None
                    }
            
            except Exception as e:
                with self.lock:
                    self.results[task_id] = {
                        "status": "failed",
                        "data": None,
                        "error": str(e)
                    }
            
            self.queue.task_done()
        
        self.processing = False
    
    def get_result(self, task_id):
        """Get the result of a specific task"""
        with self.lock:
            return self.results.get(task_id, {"status": "unknown", "data": None, "error": None})
    
    def get_all_results(self):
        """Get all completed results"""
        with self.lock:
            return {task_id: data["data"] for task_id, data in self.results.items() 
                    if data["status"] == "completed" and data["data"] is not None}
    
    def is_queue_empty(self):
        """Check if the queue is empty"""
        return self.queue.empty() and not self.processing
    
    def get_all_task_statuses(self):
        """Get the status of all tasks"""
        with self.lock:
            return {task_id: data["status"] for task_id, data in self.results.items()}


class GeminiProcessor:
    """
    Class to handle processing documents using Google's Gemini model
    with robust rate limiting and queue management
    """
    def __init__(self, api_key, model="gemini-1.5-pro"):
        self.api_key = api_key
        self.model = model
        self.rate_limiter = RateLimiter()
        self.lock = threading.Lock()
        self.queue = ProcessingQueue(self)
        
        if not GEMINI_AVAILABLE:
            print("Warning: Google Generative AI package not available. Install with pip install google-generativeai")
            return
        
        # Configure the Gemini API
        try:
            genai.configure(api_key=api_key)
        except Exception as e:
            print(f"Error configuring Gemini: {e}")
    
    def analyze_document(self, file_path):
        """
        Analyze a document using Gemini with structured output
        
        Parameters:
        - file_path: Path to the document file
        
        Returns:
        - Extracted information as a dictionary
        """
        if not GEMINI_AVAILABLE:
            return {
                'name': "Error: Google Generative AI not available",
                'email': '',
                'phone': '',
                'education': '',
                'experience': 0,
                'skills': '',
                'location': '',
                'filename': os.path.basename(file_path),
                'file_path': file_path,
                'error': "Google Generative AI package not installed"
            }
            
        try:
            # Get the filename without extension (may contain candidate name)
            filename = os.path.basename(file_path)
            name_from_filename = os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ')
            
            # Extract text from file 
            text = get_text_from_file(file_path)
            
            # Trim text if it's too long for the Gemini API
            if len(text) > 30000:  
                print(f"Warning: Document {file_path} is very long ({len(text)} chars). Truncating.")
                text = text[:30000]
            
            # Check if text extraction was successful
            if not text or len(text) < 50:
                raise ValueError(f"Failed to extract meaningful text from {file_path}. Text length: {len(text)}")
            
            # Prepare the prompt for resume parsing
            prompt = self._create_resume_parsing_prompt(text, name_from_filename)
            
            # Call Gemini API with retry logic
            response = self._call_gemini_with_retry(prompt)
            
            # Parse the response
            extracted_info = self._parse_response(response)
            
            # Add filename and file path for reference
            extracted_info['filename'] = os.path.basename(file_path)
            extracted_info['file_path'] = file_path
            
            return extracted_info
        except Exception as e:
            print(f"Error analyzing document {file_path}: {e}")
            # Return a structured error object
            return {
                'name': f"Error: {str(e)[:50]}...",
                'email': '',
                'phone': '',
                'education': '',
                'experience': 0,
                'skills': '',
                'location': '',
                'filename': os.path.basename(file_path),
                'file_path': file_path,
                'error': str(e)
            }
    
    def analyze_document_with_filters(self, file_path, user_filters):
        """
        Analyze a document using Gemini, incorporating user filter preferences
        
        Parameters:
        - file_path: Path to the document file
        - user_filters: Dictionary containing user's filter preferences
        
        Returns:
        - Extracted information as a dictionary with match score
        """
        if not GEMINI_AVAILABLE:
            return {
                'name': "Error: Google Generative AI not available",
                'email': '',
                'phone': '',
                'education': '',
                'experience': 0,
                'skills': '',
                'location': '',
                'match_score': 0,
                'filename': os.path.basename(file_path),
                'file_path': file_path,
                'error': "Google Generative AI package not installed"
            }
            
        try:
            # Get the filename without extension (may contain candidate name)
            filename = os.path.basename(file_path)
            name_from_filename = os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ')
            
            # Extract text from file
            text = get_text_from_file(file_path)
            
            if len(text) > 30000:
                text = text[:30000]
            
            if not text or len(text) < 50:
                raise ValueError(f"Failed to extract meaningful text from {file_path}.")
            
            # Create prompt with filters
            prompt = self._create_resume_parsing_prompt_with_filters(text, user_filters, name_from_filename)
            
            # Call Gemini API with retry logic
            response = self._call_gemini_with_retry(prompt)
            
            # Parse response
            extracted_info = self._parse_response(response)
            
            # Add file info
            extracted_info['filename'] = os.path.basename(file_path)
            extracted_info['file_path'] = file_path
            
            return extracted_info
        except Exception as e:
            print(f"Error analyzing document with filters {file_path}: {e}")
            return {
                'name': f"Error: {str(e)[:50]}...",
                'email': '',
                'phone': '',
                'education': '',
                'experience': 0,
                'skills': '',
                'location': '',
                'match_score': 0,
                'filename': os.path.basename(file_path),
                'file_path': file_path,
                'error': str(e)
            }
    
    def _call_gemini_with_retry(self, prompt, max_retries=3):
        """
        Call Gemini API with retries and backoff
        
        Parameters:
        - prompt: The prompt for Gemini
        - max_retries: Maximum number of retry attempts
        
        Returns:
        - Response from Gemini
        """
        if not GEMINI_AVAILABLE:
            return "Google Generative AI not available"
            
        attempts = 0
        last_exception = None
        
        while attempts < max_retries:
            try:
                # Wait according to rate limiter
                self.rate_limiter.wait()
                
                # Call Gemini
                response = self._call_gemini(prompt)
                
                # Update rate limiter on success
                self.rate_limiter.success()
                
                return response
            except Exception as e:
                last_exception = e
                attempts += 1
                
                # Update rate limiter and wait before retry
                wait_time = self.rate_limiter.failure()
                print(f"API error: {str(e)}. Retrying after {wait_time:.2f} seconds. Attempt {attempts}/{max_retries}")
                time.sleep(wait_time)
        
        # If all retries fail, raise the exception
        raise Exception(f"Maximum retries ({max_retries}) exceeded: {str(last_exception)}")
    
    def _call_gemini(self, prompt):
        """
        Call the Gemini API with the given prompt
        
        Parameters:
        - prompt: The prompt for Gemini
        
        Returns:
        - Response text from Gemini
        """
        if not GEMINI_AVAILABLE:
            return "Google Generative AI not available"
            
        try:
            model = genai.GenerativeModel(self.model)
            response = model.generate_content(
                prompt,
                generation_config={"temperature": 0.0}
            )
            return response.text
        except Exception as e:
            raise Exception(f"Gemini API call failed: {str(e)}")
    
    def queue_document_for_analysis(self, file_path, user_filters=None):
        """
        Queue a document for asynchronous analysis
        
        Parameters:
        - file_path: Path to the document file
        - user_filters: Optional dictionary containing user's filter preferences
        
        Returns:
        - Task ID for checking result status
        """
        return self.queue.add_task(file_path, user_filters)
    
    def get_queued_result(self, task_id):
        """
        Get the result of a queued document analysis
        
        Parameters:
        - task_id: Task ID returned by queue_document_for_analysis
        
        Returns:
        - Result data or status information
        """
        return self.queue.get_result(task_id)
    
    def get_all_completed_results(self):
        """
        Get all completed analysis results
        
        Returns:
        - Dictionary of completed results
        """
        return self.queue.get_all_results()
    
    def get_all_task_statuses(self):
        """
        Get the status of all tasks
        
        Returns:
        - Dictionary mapping task_id to status
        """
        return self.queue.get_all_task_statuses()
    
    def _create_resume_parsing_prompt(self, resume_text, name_hint=None):
        """
        Create a prompt for Gemini to extract information from a resume
        """
        name_hint_text = ""
        if name_hint:
            name_hint_text = f"\nHINT: The candidate's name might be '{name_hint}' based on the filename."
            
        prompt = f"""You are an expert resume parser with extensive experience in HR and technical recruiting. Extract precise information from this resume:{name_hint_text}

# EXTRACTION GUIDELINES:

## Personal Information
1. Name: Extract the full name
2. Email: Extract complete email address
3. Phone: Extract phone number with formatting
4. Location: Extract city, state/province, country information

## Professional Details
5. Work Experience:
   - Calculate total years of experience (round to nearest whole number)
   - Count internships as valid experience
   - Identify all companies and positions held
   - Extract dates of employment
   - Note key responsibilities and achievements

6. Education:
   - Extract all degrees, major fields of study
   - Extract educational institutions
   - Extract graduation years
   - Note any academic honors or GPA if mentioned

7. Technical Information:
   - Skills: Extract ALL technical skills mentioned anywhere in the resume
   - Languages: Extract all programming and human languages with proficiency levels
   - Certifications: Extract all professional certifications

# FORMAT REQUIREMENTS:

Create a clean, structured JSON object with these exact fields:
{{
  "name": string (full name),
  "email": string (complete email),
  "phone": string (full phone number),
  "location": string (complete location details),
  "experience": number (total years as integer),
  "work_history": Array of objects with company, position, dates, and responsibilities,
  "education": Array of objects with degree, institution, year, and field of study,
  "skills": Array of strings (all technical skills),
  "linkedin": string (complete URL or empty string if not present),
  "github": string (complete URL or empty string if not present),
  "languages": Array of objects with language name and proficiency level,
  "certifications": Array of strings (all certifications)  
}}

Your output must be ONLY the JSON object without any additional text. Ensure the JSON is valid and properly formatted.

RESUME TEXT:
{resume_text}
"""
        return prompt
    
    def _create_resume_parsing_prompt_with_filters(self, resume_text, user_filters, name_hint=None):
        """
        Create an enhanced prompt for Gemini to extract information and provide matching analysis
        """
        # Build filter context string
        filter_context = "The evaluator is specifically looking for candidates with these qualifications:\n"
        
        if user_filters.get('skills'):
            filter_context += f"- Skills required: {', '.join(user_filters['skills'])}\n"
        
        if user_filters.get('min_experience', 0) > 0:
            filter_context += f"- Minimum experience: {user_filters['min_experience']} years\n"
        
        if user_filters.get('education_level') and user_filters['education_level'] != "Any":
            filter_context += f"- Education level: {user_filters['education_level']} or higher\n"
        
        if user_filters.get('location'):
            filter_context += f"- Location preference: {user_filters['location']}\n"
        
        if user_filters.get('custom_filters'):
            for key, value in user_filters['custom_filters'].items():
                if value:
                    filter_context += f"- {key}: {value}\n"
        
        name_hint_text = ""
        if name_hint:
            name_hint_text = f"\nHINT: The candidate's name might be '{name_hint}' based on the filename."
        
        prompt = f"""You are an expert resume parser and talent evaluator. Extract precise information from this resume and evaluate how well the candidate matches the job requirements.{name_hint_text}

# JOB REQUIREMENTS - IMPORTANT
{filter_context}
Pay special attention to these requirements throughout your analysis.

# RESUME EXTRACTION GUIDELINES:
1. Extract all personal information accurately (name, email, phone, location)
2. Calculate total years of experience (include internships)
3. Extract all education details (degrees, institutions, years, fields of study)
4. Extract ALL technical skills mentioned throughout the resume, including in project descriptions
5. Extract work history with dates, companies, positions, and key responsibilities
6. Extract languages, certifications, and online profiles

# CANDIDATE EVALUATION GUIDELINES:
1. Give a precise match score from 0-100 based on how well the candidate matches the job requirements
2. Provide 3-5 specific reasons why the candidate is a good match, with concrete examples from their resume
3. Identify any gaps between the candidate's qualifications and the job requirements
4. Be objective and evidence-based in your evaluation

# FORMAT REQUIREMENTS:
Create a clean JSON object with these exact fields:
{{
  "name": string (full name),
  "email": string (complete email),
  "phone": string (full phone number),
  "location": string (complete location details),
  "experience": number (total years as integer),
  "work_history": Array of objects with company, position, dates, and responsibilities,
  "education": Array of objects with degree, institution, year, and field of study,
  "skills": Array of strings (all technical skills),
  "linkedin": string (complete URL),
  "github": string (complete URL),
  "languages": Array of objects with language name and proficiency level,
  "certifications": Array of strings (all certifications),
  "match_score": number between 0-100 representing how well this candidate matches the requirements,
  "match_reasons": Array of strings explaining why this candidate is a good match (with specific examples),
  "gap_analysis": Array of strings identifying skills or qualifications the candidate is missing
}}

Your output must be ONLY the JSON object without any additional text. Ensure the JSON is valid.

RESUME TEXT:
{resume_text}
"""
        return prompt
    
    def _parse_response(self, response):
        """
        Parse the response from Gemini
        
        Parameters:
        - response: The JSON response from Gemini
        
        Returns:
        - Extracted information as a dictionary
        """
        try:
            # Find the JSON object in the response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                extracted_info = json.loads(json_str)
                
                # Ensure all required fields are present
                required_fields = ['name', 'email', 'phone', 'location', 'experience', 
                                  'skills', 'work_history', 'education', 'linkedin', 'github', 
                                  'languages', 'certifications']
                
                for field in required_fields:
                    if field not in extracted_info:
                        if field in ['work_history', 'education', 'skills', 'languages', 'certifications', 'match_reasons', 'gap_analysis']:
                            extracted_info[field] = []
                        else:
                            extracted_info[field] = ""
                
                # Ensure experience is numeric
                try:
                    extracted_info['experience'] = int(extracted_info['experience']) if extracted_info.get('experience') is not None else 0
                except (ValueError, TypeError):
                    extracted_info['experience'] = 0
                
                # Format array fields to strings for compatibility with existing code
                if isinstance(extracted_info.get('skills', []), list):
                    extracted_info['skills'] = ', '.join(extracted_info.get('skills', []))
                
                # Format education array into a string
                if isinstance(extracted_info.get('education', []), list):
                    education_parts = []
                    for edu in extracted_info.get('education', []):
                        if isinstance(edu, dict):
                            edu_str = ""
                            if 'degree' in edu:
                                edu_str += edu['degree']
                            if 'institution' in edu:
                                if edu_str:
                                    edu_str += " from "
                                edu_str += edu['institution']
                            if 'year' in edu:
                                edu_str += f" ({edu['year']})"
                            if 'field' in edu:
                                edu_str += f", {edu['field']}"
                            education_parts.append(edu_str)
                    extracted_info['education'] = "; ".join(education_parts)
                
                # Format languages array into a string
                if isinstance(extracted_info.get('languages', []), list):
                    language_parts = []
                    for lang in extracted_info.get('languages', []):
                        if isinstance(lang, dict) and 'name' in lang:
                            lang_str = lang['name']
                            if 'proficiency' in lang:
                                lang_str += f" ({lang['proficiency']})"
                            language_parts.append(lang_str)
                        elif isinstance(lang, str):
                            language_parts.append(lang)
                    extracted_info['languages'] = ", ".join(language_parts)
                
                # Format certifications array into a string
                if isinstance(extracted_info.get('certifications', []), list):
                    extracted_info['certifications'] = ", ".join(extracted_info.get('certifications', []))
                
                # Add a formatted work history summary
                if isinstance(extracted_info.get('work_history', []), list) and extracted_info.get('work_history', []):
                    work_history_parts = []
                    for job in extracted_info.get('work_history', []):
                        if isinstance(job, dict):
                            job_str = ""
                            if 'position' in job:
                                job_str += job['position']
                            if 'company' in job:
                                if job_str:
                                    job_str += " at "
                                job_str += job['company']
                            if 'dates' in job:
                                job_str += f" ({job['dates']})"
                            work_history_parts.append(job_str)
                    extracted_info['work_history_summary'] = "; ".join(work_history_parts)
                else:
                    extracted_info['work_history_summary'] = ""
                
                # Format match reasons into a string if present
                if 'match_reasons' in extracted_info and isinstance(extracted_info.get('match_reasons', []), list):
                    extracted_info['match_reasons_text'] = "- " + "\n- ".join(extracted_info.get('match_reasons', []))
                else:
                    extracted_info['match_reasons_text'] = ""
                
                # Format gap analysis into a string if present
                if 'gap_analysis' in extracted_info and isinstance(extracted_info.get('gap_analysis', []), list) and extracted_info.get('gap_analysis', []):
                    extracted_info['gap_analysis_text'] = "Areas for improvement:\n- " + "\n- ".join(extracted_info.get('gap_analysis', []))
                else:
                    extracted_info['gap_analysis_text'] = "No significant gaps identified."
                    
                # Ensure match score is present
                if 'match_score' not in extracted_info:
                    extracted_info['match_score'] = 0
                
                return extracted_info
            else:
                raise ValueError("No JSON object found in response")
        except Exception as e:
            print(f"Error parsing Gemini response: {e}")
            return {
                'name': 'Unknown',
                'email': '',
                'phone': '',
                'education': '',
                'experience': 0,
                'skills': '',
                'location': '',
                'linkedin': '',
                'github': '',
                'languages': '',
                'certifications': '',
                'work_history': [],
                'work_history_summary': '',
                'match_score': 0,
                'match_reasons': [],
                'match_reasons_text': '',
                'gap_analysis': [],
                'gap_analysis_text': 'No analysis available.'
            }