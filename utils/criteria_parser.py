"""
Criteria Parser Module

This module provides functions to convert natural language job criteria 
into structured filters that can be used by the resume parser.
"""

import json
import requests
import time

def parse_criteria_text(criteria_text, api_endpoint, api_key):
    """
    Convert natural language criteria into structured filters using Azure OpenAI
    
    Parameters:
    - criteria_text: User's description of what they're looking for
    - api_endpoint: Azure OpenAI API endpoint
    - api_key: Azure OpenAI API key
    
    Returns:
    - Dictionary with structured filters
    """
    if not criteria_text or not criteria_text.strip():
        return {
            'skills': [],
            'min_experience': 0,
            'education_level': "Any",
            'location': "",
            'custom_filters': {}
        }
    
    try:
        criteria_prompt = f"""
        Convert this job requirement into structured criteria:
        
        {criteria_text}
        
        Return as JSON with these fields:
        - required_skills: Array of skills mentioned (extract ALL technical skills mentioned)
        - min_experience: Number (years) - default to 0 if not specified
        - education_level: Education level ("Any", "High School", "Bachelor's", "Master's", "PhD") - default to "Any" if not specified
        - location: Location requirement (if any) - empty string if not specified
        - other_requirements: Array of other requirements that don't fit in the above categories
        """
        
        custom_headers = {
            "Content-Type": "application/json",
            "api-key": api_key
        }
        
        custom_data = {
            "messages": [
                {"role": "system", "content": "You are an expert at converting job requirements into structured criteria for resume filtering."},
                {"role": "user", "content": criteria_prompt}
            ],
            "max_tokens": 800,
            "temperature": 0.0,
            "response_format": {"type": "json_object"}
        }
        
        # Make the API call with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    api_endpoint,
                    headers=custom_headers,
                    json=custom_data,
                    timeout=30
                )
                
                if response.status_code == 200:
                    parsed_criteria = json.loads(response.json()['choices'][0]['message']['content'])
                    
                    # Convert to structure expected by the filter function
                    structured_filters = {
                        'skills': parsed_criteria.get('required_skills', []),
                        'min_experience': int(parsed_criteria.get('min_experience', 0)),
                        'education_level': parsed_criteria.get('education_level', "Any"),
                        'location': parsed_criteria.get('location', ""),
                        'custom_filters': {}
                    }
                    
                    # Add any other requirements as notes
                    if parsed_criteria.get('other_requirements'):
                        structured_filters['notes'] = parsed_criteria.get('other_requirements')
                    
                    return structured_filters
                elif response.status_code == 429:  # Rate limit
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                    else:
                        raise Exception(f"Rate limit exceeded: {response.status_code}")
                else:
                    raise Exception(f"API returned status code {response.status_code}")
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                time.sleep(1)  # Wait before retry
    
    except Exception as e:
        print(f"Error parsing criteria: {str(e)}")
        return {
            'skills': [],
            'min_experience': 0,
            'education_level': "Any",
            'location': "",
            'custom_filters': {},
            'error': str(e)
        }

def get_criteria_description(structured_filters):
    """
    Create a human-readable description of the criteria
    
    Parameters:
    - structured_filters: Dictionary with structured filters
    
    Returns:
    - String with human-readable description
    """
    description = "Looking for candidates with:\n"
    
    if structured_filters.get('skills'):
        description += f"- Skills: {', '.join(structured_filters['skills'])}\n"
    
    if structured_filters.get('min_experience'):
        description += f"- Experience: {structured_filters['min_experience']}+ years\n"
    
    if structured_filters.get('education_level') and structured_filters['education_level'] != "Any":
        description += f"- Education: {structured_filters['education_level']} degree\n"
    
    if structured_filters.get('location'):
        description += f"- Location: {structured_filters['location']}\n"
    
    if structured_filters.get('notes'):
        if isinstance(structured_filters['notes'], list):
            description += f"- Other requirements: {', '.join(structured_filters['notes'])}\n"
        else:
            description += f"- Other requirements: {structured_filters['notes']}\n"
    
    return description
