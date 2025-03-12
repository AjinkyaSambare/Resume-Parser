import json
import streamlit as st
import re

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

def parse_criteria_with_gemini(criteria_text, processor):
    try:
        criteria_prompt = """
        Convert this job requirement into structured criteria:
        
        {}
        
        Return as JSON with these fields:
        - required_skills: Array of skills mentioned
        - min_experience: Number (years)
        - education_level: Education level ("Any", "High School", "Bachelor's", "Master's", "PhD")
        - location: Location requirement (if any)
        - other_requirements: Array of other requirements
        
        Create a clean JSON object with ONLY these exact fields. The JSON must start with {{ and end with }}.
        """.format(criteria_text)
        
        if not GEMINI_AVAILABLE or not processor:
            st.warning("Using basic criteria extraction due to missing Gemini package")
            structured_filters = extract_basic_criteria(criteria_text)
        else:
            response_text = processor._call_gemini_with_retry(criteria_prompt)
            
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                try:
                    structured_filters = json.loads(json_str)
                except json.JSONDecodeError:
                    st.warning("Could not parse Gemini response as JSON. Using basic criteria extraction instead.")
                    structured_filters = extract_basic_criteria(criteria_text)
            else:
                st.warning("Gemini response did not contain a valid JSON object. Using basic criteria extraction instead.")
                structured_filters = extract_basic_criteria(criteria_text)
        
        filter_description = "Looking for candidates with:\n"
        if structured_filters.get('required_skills'):
            filter_description += f"- Skills: {', '.join(structured_filters['required_skills'])}\n"
        if structured_filters.get('min_experience'):
            filter_description += f"- Experience: {structured_filters['min_experience']}+ years\n"
        if structured_filters.get('education_level') and structured_filters['education_level'] != "Any":
            filter_description += f"- Education: {structured_filters['education_level']} degree\n"
        if structured_filters.get('location'):
            filter_description += f"- Location: {structured_filters['location']}\n"
        if structured_filters.get('other_requirements'):
            filter_description += f"- Other: {', '.join(structured_filters['other_requirements'])}\n"
        
        st.info(filter_description)
        
        user_filters = {
            'skills': structured_filters.get('required_skills', []),
            'min_experience': int(structured_filters.get('min_experience', 0)) if structured_filters.get('min_experience') is not None else 0,
            'education_level': structured_filters.get('education_level', "Any"),
            'location': structured_filters.get('location', ""),
            'custom_filters': {}
        }
        
        return user_filters
        
    except Exception as e:
        st.error(f"Error processing criteria with Gemini: {e}")
        return {
            'skills': extract_basic_criteria(criteria_text).get('required_skills', []),
            'min_experience': extract_basic_criteria(criteria_text).get('min_experience', 0),
            'education_level': extract_basic_criteria(criteria_text).get('education_level', "Any"),
            'location': "",
            'custom_filters': {}
        }

def extract_basic_criteria(criteria_text):
    skills = []
    experience = 0
    education = "Any"
    location = ""
    
    tech_skills = ["python", "java", "javascript", "react", "node", "sql", "aws", "azure", 
                  "docker", "kubernetes", "html", "css", "c++", "c#", "php", "ruby", "go",
                  "data science", "machine learning", "ml", "ai", "artificial intelligence",
                  "deep learning", "nlp", "natural language processing", "data analytics",
                  "data visualization", "data mining", "data warehousing", "data engineering",
                  "etl", "tableau", "power bi", "excel", "word", "powerpoint", "office",
                  "linux", "unix", "windows", "mac", "ios", "android", "swift", "kotlin",
                  "salesforce", "crm", "erp", "sap", "oracle", "peoplesoft", "scrum", "agile",
                  "kanban", "lean", "six sigma", "project management", "product management"]
    
    for skill in tech_skills:
        if skill.lower() in criteria_text.lower():
            skills.append(skill.capitalize())
    
    years_pattern = r'(\d+)\s*(?:years?|yrs?)'
    years_match = re.search(years_pattern, criteria_text, re.IGNORECASE)
    if years_match:
        experience = int(years_match.group(1))
    
    edu_levels = {
        "bachelor": "Bachelor's",
        "bs": "Bachelor's",
        "ba": "Bachelor's",
        "master": "Master's",
        "ms": "Master's",
        "ma": "Master's",
        "phd": "PhD",
        "doctorate": "PhD",
        "high school": "High School"
    }
    
    for key, value in edu_levels.items():
        if key.lower() in criteria_text.lower():
            education = value
            break
    
    location_indicators = ["located in", "location:", "location is", "based in", "remote"]
    for indicator in location_indicators:
        if indicator.lower() in criteria_text.lower():
            index = criteria_text.lower().find(indicator.lower()) + len(indicator)
            location_context = criteria_text[index:index+30].strip()
            if location_context:
                location = location_context
                break
    
    return {
        "required_skills": skills,
        "min_experience": experience,
        "education_level": education,
        "location": location,
        "other_requirements": []
    }