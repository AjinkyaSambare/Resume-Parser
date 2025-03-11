def filter_resumes(resume_data, skills=None, min_experience=0, education_level=None, location=None, custom_filters=None):
    """
    Filter resumes based on various criteria
    
    Parameters:
    - resume_data: List of dictionaries containing resume information
    - skills: List of required skills
    - min_experience: Minimum years of experience required
    - education_level: Minimum education level required
    - location: Location filter
    - custom_filters: Dictionary of custom filters (column_name: filter_value)
    
    Returns:
    - Filtered list of resume dictionaries
    """
    filtered_data = []
    
    for resume in resume_data:
        # Initialize as a match and then check each filter
        is_match = True
        
        # Filter by skills
        if skills and is_match:
            resume_skills = resume.get('skills', '').lower()
            required_skills_found = all(skill.strip().lower() in resume_skills for skill in skills if skill.strip())
            if not required_skills_found:
                is_match = False
        
        # Filter by experience
        if min_experience > 0 and is_match:
            try:
                resume_experience = int(resume.get('experience', 0))
                if resume_experience < min_experience:
                    is_match = False
            except (ValueError, TypeError):
                # If experience can't be converted to int, consider it a non-match
                is_match = False
        
        # Filter by education level
        if education_level and education_level != "Any" and is_match:
            resume_education = resume.get('education', '').lower()
            education_rank = {
                "high school": 1,
                "associate's": 2,
                "bachelor's": 3,
                "master's": 4,
                "phd": 5
            }
            
            # Convert UI-friendly names to internal names
            education_level_internal = education_level.lower()
            if education_level_internal == "bachelor's":
                education_level_internal = "bachelor"
            elif education_level_internal == "master's":
                education_level_internal = "master"
            
            # Get required rank
            required_rank = 0
            for level, rank in education_rank.items():
                if level in education_level_internal.lower():
                    required_rank = rank
                    break
            
            # Check if resume meets the education requirement
            has_required_education = False
            for level, rank in education_rank.items():
                if level in resume_education and rank >= required_rank:
                    has_required_education = True
                    break
            
            # Special checks for specific degrees
            if required_rank == 3 and ("bachelor" in resume_education or "bs" in resume_education or "b.s." in resume_education or "b.a." in resume_education):
                has_required_education = True
            elif required_rank == 4 and ("master" in resume_education or "ms" in resume_education or "m.s." in resume_education or "m.a." in resume_education):
                has_required_education = True
            elif required_rank == 5 and ("phd" in resume_education or "doctor" in resume_education or "ph.d." in resume_education):
                has_required_education = True
            
            if not has_required_education:
                is_match = False
        
        # Filter by location
        if location and is_match:
            resume_location = resume.get('location', '').lower()
            if location.lower() not in resume_location:
                is_match = False
        
        # Apply custom filters
        if custom_filters and is_match:
            for column, filter_value in custom_filters.items():
                if filter_value:  # Only apply non-empty filters
                    column_value = str(resume.get(column, '')).lower()
                    if filter_value.lower() not in column_value:
                        is_match = False
                        break
        
        # Add matching resume to results
        if is_match:
            filtered_data.append(resume)
    
    return filtered_data

def rank_resumes(resume_data, criteria):
    """
    Rank resumes based on matching criteria
    
    Parameters:
    - resume_data: List of dictionaries containing resume information
    - criteria: Dictionary of criteria with weights (e.g., {'python': 2, 'java': 1})
    
    Returns:
    - List of resumes sorted by rank (highest first)
    """
    ranked_resumes = []
    
    for resume in resume_data:
        score = 0
        
        # Calculate score based on criteria
        for criterion, weight in criteria.items():
            criterion = criterion.lower()
            
            # Check skills
            if criterion in resume.get('skills', '').lower():
                score += weight
            
            # Check education
            if criterion in resume.get('education', '').lower():
                score += weight
            
            # Check experience (if criterion is a number)
            try:
                if int(criterion) <= int(resume.get('experience', 0)):
                    score += weight
            except ValueError:
                pass
        
        # Add resume with its score
        ranked_resumes.append({
            'resume': resume,
            'score': score
        })
    
    # Sort by score (descending)
    ranked_resumes.sort(key=lambda x: x['score'], reverse=True)
    
    # Return only the resume objects, now sorted
    return [item['resume'] for item in ranked_resumes]