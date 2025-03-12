import streamlit as st
import pandas as pd
import json

def filter_resumes_with_nlp(query, processor, resumes):
    """
    Filter resumes using natural language processing based on user query
    
    Args:
        query (str): User's natural language query (e.g., "Java developers with 5+ years experience")
        processor: The NLP processor instance
        resumes (list): List of resume data dictionaries
        
    Returns:
        list: Filtered list of resume data dictionaries
    """
    if not query or not resumes:
        return resumes
        
    try:
        # Convert query to structured filters
        if processor:
            filters = process_nlp_query(query, processor)
            
            # Apply filters to resumes
            filtered_resumes = []
            for resume in resumes:
                if matches_filters(resume, filters):
                    filtered_resumes.append(resume)
                    
            # If no matches through structured filtering, try basic keyword filtering as backup
            if not filtered_resumes:
                st.info("No matches found with structured filtering. Trying keyword search...")
                filtered_resumes = simple_keyword_filter(query, resumes)
        else:
            # Fallback to simple keyword filtering
            filtered_resumes = simple_keyword_filter(query, resumes)
            
        return filtered_resumes
        
    except Exception as e:
        st.error(f"Error filtering resumes: {e}")
        # Fallback to basic keyword filtering on errors
        return simple_keyword_filter(query, resumes)

def simple_keyword_filter(query, resumes):
    """
    Simple keyword-based resume filtering
    
    Args:
        query (str): User's query string
        resumes (list): List of resume data dictionaries
        
    Returns:
        list: Filtered list of resume data dictionaries
    """
    # Split the query into keywords
    keywords = [kw.strip().lower() for kw in query.split() if len(kw.strip()) > 2]
    
    if not keywords:
        # If no valid keywords, try with shorter words too
        keywords = [kw.strip().lower() for kw in query.split() if len(kw.strip()) > 0]
    
    if not keywords:
        return resumes  # Return all resumes if no keywords found
    
    st.info(f"Searching for keywords: {', '.join(keywords)}")
    
    filtered_resumes = []
    for resume in resumes:
        resume_text = str(resume).lower()
        
        # Check if any keyword appears in the resume text
        if any(keyword in resume_text for keyword in keywords):
            filtered_resumes.append(resume)
    
    return filtered_resumes

def process_nlp_query(query, processor):
    """
    Process natural language query into structured filters
    
    Args:
        query (str): User's natural language query
        processor: The NLP processor instance
        
    Returns:
        dict: Structured filters
    """
    prompt = f"""
    Extract structured filtering criteria from this search query: "{query}"
    
    Analyze the search query and extract the following information in JSON format.
    Return a valid JSON object with these fields:
    - skills: List of required skills/technologies
    - experience_years: Minimum years of experience (number)
    - education: Required education level
    - job_titles: List of relevant job titles
    - location: Location information
    - keywords: Other important keywords
    
    For any field where information is not provided, use null.
    The JSON must be properly formatted with double quotes around keys and string values.
    Do not include any text before or after the JSON.
    """
    
    try:
        result = processor._call_gemini_with_retry(prompt)
        # Clean the response to ensure it contains only valid JSON
        result = result.strip()
        
        # Try to find JSON in the response by looking for opening/closing braces
        json_start = result.find('{')
        json_end = result.rfind('}')
        
        if json_start >= 0 and json_end > json_start:
            # Extract just the JSON part
            json_str = result[json_start:json_end+1]
            filters = json.loads(json_str)
            return filters
        else:
            # Fallback to manual construction
            st.warning("Could not extract valid JSON from AI response. Using basic filtering.")
            return {
                'skills': [kw.strip() for kw in query.split(",")],
                'experience_years': 0,
                'education': None,
                'job_titles': [],
                'location': None,
                'keywords': [query]
            }
    except Exception as e:
        st.warning(f"Could not process query with AI: {str(e)}. Using basic filtering.")
        # Fallback to simple keyword matching
        return {
            'skills': [kw.strip() for kw in query.split(",")],
            'experience_years': 0,
            'education': None,
            'job_titles': [],
            'location': None,
            'keywords': [query]
        }

def matches_filters(resume, filters):
    """
    Check if a resume matches the given filters
    
    Args:
        resume (dict): Resume data
        filters (dict): Structured filters
        
    Returns:
        bool: True if the resume matches the filters
    """
    # Simple implementation - can be expanded for more sophisticated matching
    resume_text = str(resume).lower()
    
    # Skills matching
    if filters.get('skills'):
        if not any(skill.lower() in resume_text for skill in filters['skills']):
            return False
            
    # Experience matching
    if filters.get('experience_years'):
        experience = resume.get('years_of_experience', 0)
        try:
            if float(experience) < float(filters['experience_years']):
                return False
        except (ValueError, TypeError):
            # If we can't parse the experience, try text-based matching
            if str(filters['experience_years']) + "+" not in resume_text:
                return False
                
    # Education matching
    if filters.get('education') and filters['education'] is not None:
        if filters['education'].lower() not in resume_text:
            return False
            
    # Job title matching
    if filters.get('job_titles'):
        if not any(title.lower() in resume_text for title in filters['job_titles']):
            return False
            
    # Location matching
    if filters.get('location') and filters['location'] is not None:
        if filters['location'].lower() not in resume_text:
            return False
        
    # Check for generic keywords
    if filters.get('keywords'):
        if not any(keyword.lower() in resume_text for keyword in filters['keywords']):
            return False
            
    return True
