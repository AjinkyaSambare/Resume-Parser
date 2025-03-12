def filter_resumes(resume_data, skills=None, min_experience=0, education_level=None, location=None, custom_filters=None):
    if not resume_data:
        return []
        
    filtered_data = []
    
    for resume in resume_data:
        is_match = True
        
        if skills and any(skill.strip() for skill in skills) and is_match:
            resume_skills = resume.get('skills', '').lower()
            required_skills_found = all(
                skill.strip().lower() in resume_skills 
                for skill in skills if skill.strip()
            )
            
            if not required_skills_found:
                is_match = False
        
        if min_experience > 0 and is_match:
            try:
                resume_experience = int(resume.get('experience', 0)) if resume.get('experience') is not None else 0
                if resume_experience < min_experience:
                    is_match = False
            except (ValueError, TypeError):
                is_match = False
        
        if education_level and education_level != "Any" and is_match:
            resume_education = resume.get('education', '').lower()
            
            education_rank = {
                "high school": 1,
                "associate": 2,
                "bachelor": 3,
                "master": 4,
                "phd": 5,
                "doctorate": 5
            }
            
            education_level_norm = education_level.lower().replace("'s", "").replace(".", "")
            resume_education_norm = resume_education.replace("'s", "").replace(".", "")
            
            required_rank = 0
            for level, rank in education_rank.items():
                if level in education_level_norm:
                    required_rank = rank
                    break
            
            has_required_education = False
            
            for level, rank in education_rank.items():
                if level in resume_education_norm and rank >= required_rank:
                    has_required_education = True
                    break
            
            if not has_required_education:
                if required_rank <= 3 and any(term in resume_education_norm for term in ["bachelor", "bs", "ba", "b.s", "b.a"]):
                    has_required_education = True
                elif required_rank <= 4 and any(term in resume_education_norm for term in ["master", "ms", "ma", "m.s", "m.a", "mba"]):
                    has_required_education = True
                elif required_rank <= 5 and any(term in resume_education_norm for term in ["phd", "ph.d", "doctor", "doctorate"]):
                    has_required_education = True
            
            if not has_required_education:
                is_match = False
        
        if location and location.strip() and is_match:
            resume_location = resume.get('location', '').lower()
            if location.lower().strip() not in resume_location:
                is_match = False
        
        if custom_filters and is_match:
            for column, filter_value in custom_filters.items():
                if filter_value and filter_value.strip():
                    column_value = str(resume.get(column, '')).lower()
                    if filter_value.lower().strip() not in column_value:
                        is_match = False
                        break
        
        if is_match:
            filtered_data.append(resume)
    
    return filtered_data