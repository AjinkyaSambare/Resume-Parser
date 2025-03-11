import os
import streamlit as st
import pandas as pd
import time
import requests
import json
from utils.file_handler import save_uploaded_files, get_text_from_file
from utils.export import export_to_excel
from utils.secrets_manager import SecretsManager
from utils.azure_openai import AzureOpenAIProcessor

# Set page configuration
st.set_page_config(
    page_title="Resume Matcher",
    page_icon="📄",
    layout="wide"
)

# Initialize secrets manager
secrets_manager = SecretsManager()

# Initialize session state for storing data
if 'resume_data' not in st.session_state:
    st.session_state.resume_data = []
if 'matches' not in st.session_state:
    st.session_state.matches = []
if 'azure_processor' not in st.session_state:
    st.session_state.azure_processor = None
if 'azure_configured' not in st.session_state:
    st.session_state.azure_configured = secrets_manager.has_secrets()
if 'batch_size' not in st.session_state:
    st.session_state.batch_size = 5
if 'processing_files' not in st.session_state:
    st.session_state.processing_files = {}
if 'processing_complete' not in st.session_state:
    st.session_state.processing_complete = False

# Initialize persistent display columns for results
if 'display_columns' not in st.session_state:
    st.session_state.display_columns = ['filename', 'name', 'email', 'phone', 'education', 'experience', 'skills', 'match_score']

# App title and description
st.title("Resume Matcher")
st.markdown("""
This app helps you find the perfect candidates from your resume collection. 
Simply upload resumes, describe what you're looking for, and let AI do the rest.
""")

# Check Azure API configuration
if not st.session_state.azure_configured:
    st.error("""
    ⚠️ Azure OpenAI API is not configured. 
    Please add your API credentials in the .streamlit/secrets.toml file.
    """)

# Main layout with two columns
col1, col2 = st.columns([3, 1])

with col2:
    # Batch size is fixed at 5 per API requirements
    st.session_state.batch_size = 5

with col1:
    # Single input source with tabs for upload and future email fetching
    tab1, tab2 = st.tabs(["Upload Resumes", "Email Fetching (Coming Soon)"])
    
    with tab1:
        uploaded_files = st.file_uploader(
            "Upload Resumes", 
            accept_multiple_files=True,
            type=['pdf', 'docx', 'txt']
        )
    
    with tab2:
        st.info("Email fetching will be available in a future update.")
        
    # Natural language criteria input
    criteria_text = st.text_area(
        "What kind of candidates are you looking for?",
        placeholder="Example: I need Python developers with at least 3 years of experience in finance who know AWS and have a Bachelor's degree",
        height=100
    )
    
    # One-click processing button
    process_button = st.button("Find Matching Candidates", type="primary")

# Processing logic
if process_button and uploaded_files and criteria_text:
    with st.spinner("Processing resumes and finding matches..."):
        # Create necessary directories
        os.makedirs('data/uploads', exist_ok=True)
        os.makedirs('data/processed', exist_ok=True)
        
        # Save uploaded files
        file_paths = save_uploaded_files(uploaded_files)
        
        # Initialize Azure OpenAI processor if needed
        if st.session_state.azure_processor is None:
            if st.session_state.azure_configured:
                try:
                    azure_endpoint = secrets_manager.get_secret('endpoint')
                    azure_api_key = secrets_manager.get_secret('api_key')
                    st.session_state.azure_processor = AzureOpenAIProcessor(azure_endpoint, azure_api_key)
                except Exception as e:
                    st.error(f"Error initializing Azure OpenAI: {e}")
                    st.stop()
            else:
                st.error("Azure OpenAI API is required but not configured.")
                st.stop()
        
        # Parse the criteria text into structured filters
        try:
            criteria_prompt = f"""
            Convert this job requirement into structured criteria:
            
            {criteria_text}
            
            Return as JSON with these fields:
            - required_skills: Array of skills mentioned
            - min_experience: Number (years)
            - education_level: Education level ("Any", "High School", "Bachelor's", "Master's", "PhD")
            - location: Location requirement (if any)
            - other_requirements: Array of other requirements
            """
            
            custom_headers = {
                "Content-Type": "application/json",
                "api-key": secrets_manager.get_secret('api_key')
            }
            
            custom_data = {
                "messages": [
                    {"role": "system", "content": "You are an expert at converting job requirements into structured criteria."},
                    {"role": "user", "content": criteria_prompt}
                ],
                "max_tokens": 500,
                "temperature": 0.0,
                "response_format": {"type": "json_object"}
            }
            
            try:
                response = requests.post(
                    secrets_manager.get_secret('endpoint'),
                    headers=custom_headers,
                    json=custom_data,
                    timeout=30
                )
                
                # Add retry logic for rate limiting
                retry_count = 0
                max_retries = 3
                
                while response.status_code == 429 and retry_count < max_retries:
                    wait_time = (2 ** retry_count) * 5  # Exponential backoff
                    st.warning(f"Rate limit reached. Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                    
                    response = requests.post(
                        secrets_manager.get_secret('endpoint'),
                        headers=custom_headers,
                        json=custom_data,
                        timeout=30
                    )
                    retry_count += 1
                
                if response.status_code == 200:
                    structured_filters = json.loads(response.json()['choices'][0]['message']['content'])
                    
                    # Create a more readable version of the filters
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
                    
                    # Display the criteria to the user
                    st.info(filter_description)
                    
                    # Format for API
                    user_filters = {
                        'skills': structured_filters.get('required_skills', []),
                        'min_experience': int(structured_filters.get('min_experience', 0)) if structured_filters.get('min_experience') is not None else 0,
                        'education_level': structured_filters.get('education_level', "Any"),
                        'location': structured_filters.get('location', ""),
                        'custom_filters': {}
                    }
                    
                    # Save filters to session state for later use
                    st.session_state.user_filters = user_filters
                else:
                    st.error(f"Error processing criteria: API returned status code {response.status_code}")
                    user_filters = {
                        'skills': [],
                        'min_experience': 0,
                        'education_level': "Any",
                        'location': "",
                        'custom_filters': {}
                    }
            except Exception as e:
                st.error(f"Error calling Azure OpenAI API: {e}")
                user_filters = {
                    'skills': [],
                    'min_experience': 0,
                    'education_level': "Any",
                    'location': "",
                    'custom_filters': {}
                }
        except Exception as e:
            st.error(f"Error processing criteria: {e}")
            user_filters = {
                'skills': [],
                'min_experience': 0,
                'education_level': "Any",
                'location': "",
                'custom_filters': {}
            }
        
        # Process files with the structured criteria context
        azure_processor = st.session_state.azure_processor
        total_files = len(file_paths)
        batch_size = st.session_state.batch_size
        
        # Set up progress tracking
        status_container = st.empty()
        progress_bar = st.progress(0)
        file_status = st.empty()
        
        status_container.info(f"Processing {total_files} resumes...")
        
        # Reset session data
        st.session_state.processing_complete = False
        st.session_state.processing_files = {}
        st.session_state.resume_data = []
        
        # Process files in batches
        for i in range(0, total_files, batch_size):
            batch = file_paths[i:i+batch_size]
            
            # Queue batch for processing
            task_ids = []
            for file_path in batch:
                file_name = os.path.basename(file_path)
                task_id = azure_processor.queue_document_for_analysis(file_path, user_filters)
                task_ids.append(task_id)
                st.session_state.processing_files[task_id] = {
                    "file_path": file_path,
                    "file_name": file_name,
                    "status": "queued"
                }
            
            # Monitor batch progress
            batch_complete = False
            while not batch_complete:
                # Check task statuses
                for task_id in task_ids:
                    result = azure_processor.get_queued_result(task_id)
                    
                    if result["status"] == "completed":
                        if st.session_state.processing_files[task_id]["status"] != "complete":
                            st.session_state.processing_files[task_id]["status"] = "complete"
                            if result["data"]:
                                st.session_state.resume_data.append(result["data"])
                    elif result["status"] == "failed":
                        st.session_state.processing_files[task_id]["status"] = "error"
                        st.session_state.processing_files[task_id]["error"] = result["error"]
                
                # Update progress
                completed = sum(1 for task in st.session_state.processing_files.values() 
                              if task["status"] in ["complete", "error"])
                progress = completed / total_files
                progress_bar.progress(progress, text=f"Processed {completed}/{total_files} resumes")
                
                # Update status text
                status_text = ""
                for task_id in task_ids:
                    task = st.session_state.processing_files[task_id]
                    icon = "⏳" if task["status"] == "queued" else "✅" if task["status"] == "complete" else "❌"
                    status_text += f"{icon} {task['file_name']}: {task['status'].upper()}\n"
                file_status.code(status_text)
                
                # Check if batch is complete
                batch_complete = all(st.session_state.processing_files[task_id]["status"] in ["complete", "error"] 
                                  for task_id in task_ids)
                
                # Wait before checking again
                if not batch_complete:
                    time.sleep(1)
        
        # All processing complete
        st.session_state.processing_complete = True
        
        # Final status
        completed = sum(1 for task in st.session_state.processing_files.values() 
                      if task["status"] == "complete")
        errors = sum(1 for task in st.session_state.processing_files.values() 
                   if task["status"] == "error")
        
        progress_bar.progress(1.0, text="Processing complete!")
        
        if errors > 0:
            status_container.warning(f"Processed {completed}/{total_files} resumes. {errors} had errors.")
        else:
            status_container.success(f"Successfully processed all {total_files} resumes!")
        
        # Filter processed resumes to show only those that match the criteria
        from utils.filters import filter_resumes
        st.session_state.matches = filter_resumes(
            st.session_state.resume_data,
            skills=st.session_state.user_filters.get('skills', []),
            min_experience=st.session_state.user_filters.get('min_experience', 0),
            education_level=st.session_state.user_filters.get('education_level', 'Any'),
            location=st.session_state.user_filters.get('location', ''),
            custom_filters=st.session_state.user_filters.get('custom_filters', {})
        )
        
        # Sort matches by match score (descending)
        st.session_state.matches.sort(key=lambda x: x.get('match_score', 0), reverse=True)

# Processing status indicators
elif process_button and not uploaded_files:
    st.warning("Please upload at least one resume file.")
elif process_button and not criteria_text:
    st.warning("Please describe what kind of candidates you're looking for.")

# Check for processing in progress
if 'processing_files' in st.session_state and st.session_state.processing_files and not st.session_state.processing_complete:
    # Calculate progress
    azure_processor = st.session_state.azure_processor
    if azure_processor:
        # Update statuses
        task_statuses = azure_processor.get_all_task_statuses()
        
        for task_id, status in task_statuses.items():
            if task_id in st.session_state.processing_files:
                prev_status = st.session_state.processing_files[task_id]["status"]
                if status == "completed" and prev_status != "complete":
                    result = azure_processor.get_queued_result(task_id)
                    st.session_state.processing_files[task_id]["status"] = "complete"
                    if result["data"] and result["data"] not in st.session_state.resume_data:
                        st.session_state.resume_data.append(result["data"])
                elif status == "failed" and prev_status != "error":
                    result = azure_processor.get_queued_result(task_id)
                    st.session_state.processing_files[task_id]["status"] = "error"
                    st.session_state.processing_files[task_id]["error"] = result.get("error", "Unknown error")
    
    # Show progress
    total_files = len(st.session_state.processing_files)
    completed = sum(1 for task in st.session_state.processing_files.values() 
                  if task["status"] in ["complete", "error"])
    progress = completed / total_files if total_files > 0 else 0
    
    st.info(f"Resume processing in progress: {completed}/{total_files} complete")
    st.progress(progress)
    
    # Status of each file
    status_text = ""
    for task_id, task in st.session_state.processing_files.items():
        icon = "⏳" if task["status"] == "queued" else "✅" if task["status"] == "complete" else "❌"
        status_text += f"{icon} {task['file_name']}: {task['status'].upper()}\n"
    st.code(status_text)
    
    # Mark as complete if all done
    if completed == total_files:
        st.session_state.processing_complete = True
        st.success("Processing complete!")
        
        # Apply filters to show only matching resumes
        if 'user_filters' in st.session_state:
            filters_to_use = st.session_state.user_filters
        else:
            # If user_filters isn't available in session state,
            # use empty filters as fallback
            filters_to_use = {
                'skills': [],
                'min_experience': 0,
                'education_level': 'Any',
                'location': '',
                'custom_filters': {}
            }
            
        from utils.filters import filter_resumes
        st.session_state.matches = filter_resumes(
            st.session_state.resume_data,
            skills=filters_to_use.get('skills', []),
            min_experience=filters_to_use.get('min_experience', 0),
            education_level=filters_to_use.get('education_level', 'Any'),
            location=filters_to_use.get('location', ''),
            custom_filters=filters_to_use.get('custom_filters', {})
        )
        
        st.session_state.matches.sort(key=lambda x: x.get('match_score', 0), reverse=True)
    
    # Add refresh button
    if st.button("Refresh Status"):
        st.rerun()

# Results section
if 'matches' in st.session_state and st.session_state.matches:
    st.header("Matching Candidates")
    
    # Convert matches to DataFrame and ensure all persistent display columns exist
    df = pd.DataFrame(st.session_state.matches)
    for col in st.session_state.display_columns:
        if col not in df.columns:
            df[col] = ""
    
    # Custom column addition
    with st.expander("Add Custom Information"):
        col1, col2 = st.columns([3, 1])
        with col1:
            new_column = st.text_input("What information would you like to extract?", 
                                     placeholder="e.g., Years of Python experience")
        with col2:
            add_column_button = st.button("Add Column")
    
        if add_column_button and new_column:
            with st.spinner(f"Extracting {new_column}..."):
                # Process new column for each resume
                azure_processor = st.session_state.azure_processor
                
                for resume in st.session_state.matches:
                    file_path = resume.get('file_path', "")
                    try:
                        # Get resume text
                        text = get_text_from_file(file_path)
                        
                        # Create extraction prompt
                        custom_prompt = f"""You are extracting specific information from a resume.

TASK: {new_column}

Resume text:
{text[:7000]}

Provide ONLY the requested information as plain text. Be precise and thorough.
If the information cannot be found, state "Not found in resume".
Do not include explanations, analysis, or any additional text."""
                        
                        try:
                            custom_headers = {
                                "Content-Type": "application/json",
                                "api-key": secrets_manager.get_secret('api_key')
                            }
                            
                            custom_data = {
                                "messages": [
                                    {"role": "system", "content": "You are an expert resume analyzer."},
                                    {"role": "user", "content": custom_prompt}
                                ],
                                "max_tokens": 500,
                                "temperature": 0.0
                            }
                            
                            max_retries = 3
                            for attempt in range(max_retries):
                                try:
                                    response = requests.post(
                                        secrets_manager.get_secret('endpoint'),
                                        headers=custom_headers,
                                        json=custom_data,
                                        timeout=30
                                    )
                                    
                                    if response.status_code == 200:
                                        result = response.json()['choices'][0]['message']['content'].strip()
                                        resume[new_column] = result
                                        break
                                    elif response.status_code == 429:  # Rate limit
                                        wait_time = (2 ** attempt) * 5  # Exponential backoff
                                        time.sleep(wait_time)
                                        if attempt == max_retries - 1:
                                            resume[new_column] = f"Rate limit exceeded: {response.status_code}"
                                    else:
                                        resume[new_column] = f"Error: API returned status code {response.status_code}"
                                        break
                                except Exception as e:
                                    if attempt == max_retries - 1:
                                        resume[new_column] = f"Error: {str(e)[:50]}"
                                    time.sleep(5)
                        except Exception as e:
                            resume[new_column] = f"Error: {str(e)[:50]}"
                    except Exception as e:
                        resume[new_column] = f"Error processing: {str(e)[:50]}"
                
                # Update persistent display columns and recreate DataFrame
                if new_column not in st.session_state.display_columns:
                    st.session_state.display_columns.append(new_column)
                df = pd.DataFrame(st.session_state.matches)
                st.success(f"Added column: {new_column}")
                st.rerun()
    
    # Display results table
    st.dataframe(df[st.session_state.display_columns], use_container_width=True)
    
    # Match scores visualization
    if 'match_score' in df.columns and df['match_score'].sum() > 0:
        st.subheader("Match Score Analysis")
        
        import plotly.express as px
        match_scores = df[['name', 'match_score']].sort_values('match_score', ascending=False)
        fig = px.bar(
            match_scores, 
            x='name', 
            y='match_score',
            title="Candidate Match Scores",
            labels={'match_score': 'Match Score (%)', 'name': 'Candidate'},
            color='match_score',
            color_continuous_scale='Viridis',
            range_color=[0, 100]
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Match reasons for top candidates
        st.subheader("Why These Candidates Match")
        
        for idx, row in df.sort_values('match_score', ascending=False).head(3).iterrows():
            if row['match_score'] > 0:
                with st.expander(f"{row['name']} - Match Score: {row['match_score']}%"):
                    if 'match_reasons_text' in row and row['match_reasons_text']:
                        st.markdown(row['match_reasons_text'])
                    else:
                        st.info("No detailed match information available")
    
    # Export functionality
    st.subheader("Export Results")
    try:
        excel_data = export_to_excel(df[st.session_state.display_columns])
        if st.download_button(
            label="Export to Excel",
            data=excel_data,
            file_name="matching_candidates.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        ):
            st.success("Export successful!")
    except Exception as e:
        st.error(f"Error exporting to Excel: {e}")

# No data state
if not uploaded_files and not st.session_state.resume_data:
    st.info("Please upload resume files and describe what kind of candidates you're looking for to get started.")
