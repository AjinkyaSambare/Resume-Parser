import os
import streamlit as st
import pandas as pd
import time
import requests
from utils.file_handler import save_uploaded_files, get_text_from_file
from utils.filters import filter_resumes
from utils.export import export_to_excel
from utils.secrets_manager import SecretsManager
# Import the enhanced Azure OpenAI processor
from utils.azure_openai import AzureOpenAIProcessor

# Set page configuration
st.set_page_config(
    page_title="Resume Parser",
    page_icon="📄",
    layout="wide"
)

# Initialize secrets manager
secrets_manager = SecretsManager()

# Initialize session state for storing resume data
if 'resume_data' not in st.session_state:
    st.session_state.resume_data = []
if 'filtered_data' not in st.session_state:
    st.session_state.filtered_data = []
if 'selected_columns' not in st.session_state:
    st.session_state.selected_columns = ['name', 'email', 'phone', 'education', 'experience', 'skills', 'work_history_summary', 'match_score']
if 'custom_columns' not in st.session_state:
    st.session_state.custom_columns = {}
if 'azure_processor' not in st.session_state:
    st.session_state.azure_processor = None
if 'azure_configured' not in st.session_state:
    st.session_state.azure_configured = secrets_manager.has_secrets()
if 'batch_size' not in st.session_state:
    st.session_state.batch_size = 5  # Process 5 files at a time by default
if 'processing_files' not in st.session_state:
    st.session_state.processing_files = {}  # Store info about files being processed
if 'processing_complete' not in st.session_state:
    st.session_state.processing_complete = False

# App title and description
st.title("AI-Powered Resume Parser")
st.markdown("""
### Intelligent resume parsing, filtering, and analysis

This application uses Azure OpenAI GPT-4o to extract detailed information from resumes with high accuracy.
You can upload multiple PDF, DOCX, or TXT files, customize the extraction fields, and filter candidates based on your criteria.

**Key Features:**
- 📊 Detailed data extraction including work history, education, skills, and more
- 🔍 Advanced filtering capabilities
- 🧠 Custom field extraction using AI
- 📈 Skills visualization and candidate comparison
- 📁 Export to Excel or CSV

**Get started by configuring your Azure OpenAI API and uploading resumes using the sidebar.**
""")

# Azure API configuration status
if not st.session_state.azure_configured:
    st.error("""
    ⚠️ Azure OpenAI API is not configured. 
    Please add your API credentials in the .streamlit/secrets.toml file.
    This application requires Azure OpenAI for resume parsing.
    """)

# Sidebar for configuration
with st.sidebar:
    st.header("Configuration")
    
    # Add a reset button in the sidebar
    if st.button("Reset Application", help="Clear all data and start over"):
        # Clear session state except for configuration
        for key in list(st.session_state.keys()):
            if key not in ['azure_configured']:
                del st.session_state[key]
        st.session_state.azure_processor = None
        st.session_state.resume_data = []
        st.session_state.filtered_data = []
        st.session_state.selected_columns = ['name', 'email', 'phone', 'education', 'experience', 'skills', 'work_history_summary', 'match_score']
        st.session_state.custom_columns = {}
        st.session_state.processing_files = {}
        st.session_state.processing_complete = False
        st.session_state.batch_size = 5
        st.experimental_rerun()
    
    # Azure API is required
    if not st.session_state.azure_configured:
        st.error("Azure OpenAI API credentials are required. Please configure them in .streamlit/secrets.toml")
    else:
        st.success("✅ Azure OpenAI GPT-4o is configured and ready to use.")
    
    # Batch size selection
    st.subheader("Processing Settings")
    batch_size = st.slider("Batch Size", min_value=1, max_value=10, value=st.session_state.batch_size, 
                           help="Number of resumes to process simultaneously. Lower values reduce API rate limit errors.")
    st.session_state.batch_size = batch_size
    
    # File uploader
    uploaded_files = st.file_uploader(
        "Upload Resumes", 
        accept_multiple_files=True,
        type=['pdf', 'docx', 'txt']
    )
    
    # Process button
    process_button = st.button("Process Resumes")
    
    st.divider()
    
    # Column selection
    st.subheader("Select Columns to Display")
    all_possible_columns = [
        'name', 'email', 'phone', 'education', 'experience', 'skills', 
        'location', 'linkedin', 'github', 'languages', 'certifications',
        'work_history_summary', 'match_score'
    ]
    
    selected_columns = []
    for col in all_possible_columns:
        if st.checkbox(col.capitalize(), value=(col in st.session_state.selected_columns)):
            selected_columns.append(col)
    
    # Custom column creation
    st.subheader("Add Custom Column")
    new_column = st.text_input("Column Name")
    column_prompt = st.text_area("Extraction Prompt (e.g., 'Extract years of Python experience')")
    
    if st.button("Add Custom Column") and new_column and column_prompt:
        st.session_state.custom_columns[new_column] = column_prompt
        st.success(f"Added custom column: {new_column}")
    
    # Show current custom columns
    if st.session_state.custom_columns:
        st.subheader("Custom Columns")
        for col, prompt in st.session_state.custom_columns.items():
            st.write(f"**{col}**: {prompt}")
            if st.button(f"Remove {col}"):
                del st.session_state.custom_columns[col]
                st.experimental_rerun()

# Main content
if process_button and uploaded_files:
    with st.spinner("Preparing files for processing..."):
        # Create necessary directories
        os.makedirs('data/uploads', exist_ok=True)
        os.makedirs('data/processed', exist_ok=True)
        
        # Save uploaded files
        file_paths = save_uploaded_files(uploaded_files)
        
        # Initialize Azure OpenAI processor - required for this application
        if st.session_state.azure_processor is None:
            if st.session_state.azure_configured:
                try:
                    azure_endpoint = secrets_manager.get_secret('endpoint')
                    azure_api_key = secrets_manager.get_secret('api_key')
                    st.session_state.azure_processor = AzureOpenAIProcessor(azure_endpoint, azure_api_key)
                    st.info("Using Azure OpenAI GPT-4o for processing with smart rate limiting")
                except Exception as e:
                    st.error(f"Error initializing Azure OpenAI: {e}")
                    st.stop()
            else:
                st.error("Azure OpenAI API is required but not configured.")
                st.stop()
        
        # Use the enhanced azure processor from session state
        azure_processor = st.session_state.azure_processor
        
        # Reset processing status
        st.session_state.processing_complete = False
        st.session_state.processing_files = {}
        st.session_state.resume_data = []
        
        # Create a container for processing status
        status_container = st.empty()
        progress_bar = st.progress(0)
        file_status = st.empty()
        
        # Queue all files for processing
        total_files = len(file_paths)
        batch_size = st.session_state.batch_size
        
        status_container.info(f"Queuing {total_files} files for processing in batches of {batch_size}...")
        
        # Queue files in batches to avoid overwhelming the system
        for i in range(0, total_files, batch_size):
            batch = file_paths[i:i+batch_size]
            
            # Queue this batch
            task_ids = []
            for file_path in batch:
                file_name = os.path.basename(file_path)
                task_id = azure_processor.queue_document_for_analysis(file_path)
                task_ids.append(task_id)
                st.session_state.processing_files[task_id] = {
                    "file_path": file_path,
                    "file_name": file_name,
                    "status": "queued"
                }
            
            # Monitor progress until this batch is complete
            batch_complete = False
            while not batch_complete:
                # Check the status of all tasks in this batch
                for task_id in task_ids:
                    result = azure_processor.get_queued_result(task_id)
                    
                    # Update status in session state
                    if result["status"] == "completed":
                        if st.session_state.processing_files[task_id]["status"] != "complete":
                            st.session_state.processing_files[task_id]["status"] = "complete"
                            # Add to resume data
                            st.session_state.resume_data.append(result["data"])
                    elif result["status"] == "failed":
                        st.session_state.processing_files[task_id]["status"] = "error"
                        st.session_state.processing_files[task_id]["error"] = result["error"]
                
                # Calculate overall progress
                completed = sum(1 for task in st.session_state.processing_files.values() 
                              if task["status"] in ["complete", "error"])
                progress = completed / total_files
                progress_bar.progress(progress, text=f"Processed {completed}/{total_files} resumes")
                
                # Update status of each file in this batch
                status_text = ""
                for task_id in task_ids:
                    task = st.session_state.processing_files[task_id]
                    status_icon = "⏳" if task["status"] == "queued" else "✅" if task["status"] == "complete" else "❌"
                    status_text += f"{status_icon} {task['file_name']}: {task['status'].upper()}\n"
                file_status.code(status_text)
                
                # Check if batch is complete
                batch_complete = all(st.session_state.processing_files[task_id]["status"] in ["complete", "error"] 
                                  for task_id in task_ids)
                
                # Pause before checking again
                if not batch_complete:
                    time.sleep(1)
        
        # All batches complete
        st.session_state.processing_complete = True
        
        # Final status update
        completed = sum(1 for task in st.session_state.processing_files.values() 
                      if task["status"] == "complete")
        errors = sum(1 for task in st.session_state.processing_files.values() 
                   if task["status"] == "error")
        
        progress_bar.progress(1.0, text=f"Processing complete!")
        
        if errors > 0:
            status_container.warning(f"Processed {completed}/{total_files} resumes successfully. {errors} resumes had errors.")
        else:
            status_container.success(f"Successfully processed all {total_files} resumes!")
        
        # Process custom columns if needed
        if azure_processor and st.session_state.custom_columns and st.session_state.resume_data:
            with st.spinner("Processing custom columns..."):
                for resume in st.session_state.resume_data:
                    file_path = resume['file_path']
                    for col_name, prompt in st.session_state.custom_columns.items():
                        try:
                            # Extract text from file
                            text = get_text_from_file(file_path)
                            
                            # Create a custom prompt for this column
                            custom_prompt = f"""You are extracting specific information from a resume.
                            
                            TASK: {prompt}
                            
                            Resume text:
                            {text[:7000]}
                            
                            Provide ONLY the requested information as plain text. Be precise and thorough.
                            If the information cannot be found, state "Not found in resume".
                            Do not include explanations, analysis, or any additional text."""
                            
                            # Call Azure OpenAI with rate limiting
                            try:
                                # Wait before making this additional API call
                                time.sleep(2)  # Simple rate limiting
                                
                                custom_headers = {
                                    "Content-Type": "application/json",
                                    "api-key": secrets_manager.get_secret('api_key')
                                }
                                
                                custom_data = {
                                    "messages": [
                                        {"role": "system", "content": "You are an expert resume analyzer. Extract specific information based on the prompt."},
                                        {"role": "user", "content": custom_prompt}
                                    ],
                                    "max_tokens": 500,
                                    "temperature": 0.0
                                }
                                
                                # Try up to 3 times with increasing delays
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
                                            resume[col_name] = result
                                            break
                                        elif response.status_code == 429:  # Rate limit
                                            wait_time = (2 ** attempt) * 5  # Exponential backoff: 5, 10, 20 seconds
                                            time.sleep(wait_time)
                                            if attempt == max_retries - 1:  # Last attempt
                                                resume[col_name] = f"Rate limit exceeded: {response.status_code}"
                                        else:
                                            resume[col_name] = f"Error: API returned status code {response.status_code}"
                                            break
                                    except Exception as e:
                                        if attempt == max_retries - 1:  # Last attempt
                                            resume[col_name] = f"Error: {str(e)[:50]}"
                                        time.sleep(5)  # Wait before retry
                            except Exception as e:
                                resume[col_name] = f"Error: {str(e)[:50]}"
                        except Exception as e:
                            resume[col_name] = f"Error processing custom column: {str(e)[:50]}"

# Check for processing in progress
if 'processing_files' in st.session_state and st.session_state.processing_files and not st.session_state.processing_complete:
    # Calculate progress
    azure_processor = st.session_state.azure_processor
    if azure_processor:
        # Get latest statuses
        task_statuses = azure_processor.get_all_task_statuses()
        
        # Update local processing files
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
    
    # Calculate progress
    total_files = len(st.session_state.processing_files)
    completed = sum(1 for task in st.session_state.processing_files.values() 
                  if task["status"] in ["complete", "error"])
    progress = completed / total_files if total_files > 0 else 0
    
    # Display progress
    st.info(f"Resume processing in progress: {completed}/{total_files} complete")
    st.progress(progress)
    
    # Show status of each file
    status_text = ""
    for task_id, task in st.session_state.processing_files.items():
        status_icon = "⏳" if task["status"] == "queued" else "✅" if task["status"] == "complete" else "❌"
        status_text += f"{status_icon} {task['file_name']}: {task['status'].upper()}\n"
    st.code(status_text)
    
    # Mark as complete if all files are done
    if completed == total_files:
        st.session_state.processing_complete = True
        st.success("Processing complete!")
    
    # Add a refresh button
    if st.button("Refresh Status"):
        st.experimental_rerun()

# Filter section
if st.session_state.resume_data:
    st.header("Filter Resumes")
    st.info(f"Found {len(st.session_state.resume_data)} resumes. Apply filters to narrow down candidates.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Skills filter
        skills_filter = st.text_input("Required Skills (comma-separated)", "")
        min_experience = st.number_input("Minimum Years of Experience", min_value=0, value=0)
    
    with col2:
        # Education filter
        education_level = st.selectbox(
            "Minimum Education Level",
            ["Any", "High School", "Bachelor's", "Master's", "PhD"]
        )
        
        location_filter = st.text_input("Location Contains", "")
    
    # Additional custom filters based on custom columns
    custom_filters = {}
    if st.session_state.custom_columns:
        st.subheader("Custom Filters")
        for col_name in st.session_state.custom_columns.keys():
            custom_filters[col_name] = st.text_input(f"Filter by {col_name}", "")
    
    # Apply filters button
    user_filters = {
        'skills': skills_filter.split(",") if skills_filter else [],
        'min_experience': min_experience,
        'education_level': education_level,
        'location': location_filter,
        'custom_filters': custom_filters
    }
    
    if st.button("Apply Filters"):
        with st.spinner("Filtering resumes..."):
            # Store the filters for later use
            st.session_state.last_filters = user_filters.copy()
            
            # Log filter criteria
            st.write(f"Filter criteria: Skills={user_filters['skills']}, Experience={user_filters['min_experience']}, "
                    f"Education={user_filters['education_level']}, Location={user_filters['location']}")
            
            # Filter the data
            filtered_data = filter_resumes(
                st.session_state.resume_data,
                skills=user_filters['skills'],
                min_experience=user_filters['min_experience'],
                education_level=user_filters['education_level'],
                location=user_filters['location'],
                custom_filters=user_filters['custom_filters']
            )
            
            st.session_state.filtered_data = filtered_data
            
            # Display filter results with debugging options
            if filtered_data:
                st.success(f"Found {len(filtered_data)} matching resumes!")
            else:
                st.warning("No matching resumes found. Try adjusting your filter criteria.")
                
                # Debug option
                with st.expander("Show Filter Debugging Information"):
                    st.write("Filter criteria details:")
                    st.json(user_filters)
                    
                    if st.session_state.resume_data:
                        st.write("Sample resume data:")
                        sample_resume = st.session_state.resume_data[0]
                        st.json({
                            'name': sample_resume.get('name', ''),
                            'skills': sample_resume.get('skills', ''),
                            'experience': sample_resume.get('experience', ''),
                            'education': sample_resume.get('education', ''),
                            'location': sample_resume.get('location', '')
                        })

    # Allow reprocessing with filters for better analysis
    if 'last_filters' in st.session_state and st.session_state.last_filters and st.session_state.resume_data:
        if st.button("Reanalyze with Filter Context"):
            with st.spinner("Reprocessing resumes with filter context to improve analysis..."):
                # Get the Azure processor
                azure_processor = st.session_state.azure_processor
                
                # Create a status container
                status_container = st.empty()
                progress_bar = st.progress(0)
                
                # Process each resume with filter context
                total_resumes = len(st.session_state.resume_data)
                for idx, resume in enumerate(st.session_state.resume_data):
                    # Update progress
                    progress_percentage = (idx / total_resumes)
                    progress_bar.progress(progress_percentage, text=f"Reprocessing {idx+1}/{total_resumes}...")
                    status_container.info(f"Reanalyzing: {resume.get('name', 'Unknown')} ({resume.get('filename', 'Unknown')})")
                    
                    file_path = resume['file_path']
                    
                    # Process with Azure OpenAI, incorporating user filters for better analysis
                    try:
                        # Queue for analysis with filters
                        task_id = azure_processor.queue_document_for_analysis(file_path, st.session_state.last_filters)
                        
                        # Wait for result with timeout
                        max_wait = 60  # Maximum wait time in seconds
                        start_time = time.time()
                        result = None
                        
                        while time.time() - start_time < max_wait:
                            task_result = azure_processor.get_queued_result(task_id)
                            if task_result["status"] == "completed" and task_result["data"] is not None:
                                result = task_result["data"]
                                break
                            elif task_result["status"] == "failed":
                                break
                            time.sleep(1)
                        
                        # Update the resume data if we got a result
                        if result:
                            st.session_state.resume_data[idx].update(result)
                    except Exception as e:
                        status_container.error(f"Error reanalyzing {resume.get('filename', 'Unknown')}: {str(e)}")
                
                # Complete the progress bar
                progress_bar.progress(1.0, text="Reprocessing complete!")
                
                # Reapply filters to the updated data
                filtered_data = filter_resumes(
                    st.session_state.resume_data,
                    skills=st.session_state.last_filters['skills'],
                    min_experience=st.session_state.last_filters['min_experience'],
                    education_level=st.session_state.last_filters['education_level'],
                    location=st.session_state.last_filters['location'],
                    custom_filters=st.session_state.last_filters['custom_filters']
                )
                
                st.session_state.filtered_data = filtered_data
                status_container.success(f"Reanalysis complete! Found {len(filtered_data)} matching resumes with improved analysis.")

# Results section
if st.session_state.filtered_data:
    st.header("Results")
    
    # Prepare data for display
    display_columns = selected_columns + list(st.session_state.custom_columns.keys())
    if not display_columns:
        display_columns = ['name', 'email', 'phone', 'skills']
    
    # Add filename to display columns if not already there
    if 'filename' not in display_columns:
        display_columns = ['filename'] + display_columns
    
    # Convert to DataFrame for display
    df = pd.DataFrame(st.session_state.filtered_data)
    
    # Ensure all columns exist
    for col in display_columns:
        if col not in df.columns:
            df[col] = ""
    
    # Display results table
    st.dataframe(df[display_columns], use_container_width=True)
    
    # Match reasons and scores section (only shown if processing used filters)
    if 'match_score' in df.columns and df['match_score'].sum() > 0:
        st.subheader("Match Analysis")
        
        # Create a match score visualizer
        match_scores = df[['name', 'match_score']].sort_values('match_score', ascending=False)
        
        # Display match scores as a bar chart
        import plotly.express as px
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
        
        # Show match reasons for top candidates
        st.subheader("Why These Candidates Match")
        
        for idx, row in df.sort_values('match_score', ascending=False).head(3).iterrows():
            if row['match_score'] > 0:
                with st.expander(f"{row['name']} - Match Score: {row['match_score']}%"):
                    if 'match_reasons_text' in row and row['match_reasons_text']:
                        st.markdown(row['match_reasons_text'])
                    else:
                        st.info("No detailed match information available")
    
    # Skills visualization section
    st.subheader("Skills Analysis")
    
    # Create tabs for different visualizations
    viz_tab1, viz_tab2 = st.tabs(["Skills Distribution", "Resume Comparison"])
    
    with viz_tab1:
        # Process skills data
        all_skills = []
        for resume in st.session_state.filtered_data:
            if 'skills' in resume and resume['skills']:
                skills_list = [skill.strip() for skill in resume['skills'].split(',')]
                all_skills.extend(skills_list)
        
        # Count skills frequency
        if all_skills:
            from collections import Counter
            skill_counts = Counter(all_skills)
            top_skills = dict(skill_counts.most_common(15))
            
            # Create bar chart
            import plotly.express as px
            fig = px.bar(
                x=list(top_skills.keys()),
                y=list(top_skills.values()),
                labels={'x': 'Skills', 'y': 'Frequency'},
                title='Top 15 Skills Across All Resumes',
                color=list(top_skills.values()),
                color_continuous_scale='Viridis'
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No skills data available for visualization")
    
    with viz_tab2:
        # Get candidates for comparison
        if len(df) > 1:
            selected_candidates = st.multiselect(
                "Select candidates to compare",
                options=df['name'].tolist(),
                max_selections=5
            )
            
            if selected_candidates:
                # Compare selected candidates
                comparison_data = {}
                for candidate in selected_candidates:
                    candidate_data = df[df['name'] == candidate].iloc[0]
                    if 'skills' in candidate_data and candidate_data['skills']:
                        skills_list = [skill.strip() for skill in candidate_data['skills'].split(',')]
                        comparison_data[candidate] = skills_list
                
                # Find common and unique skills
                if len(comparison_data) > 1:
                    st.subheader("Skills Comparison")
                    
                    # Create a comparison table
                    import pandas as pd
                    all_skills_set = set()
                    for skills in comparison_data.values():
                        all_skills_set.update(skills)
                    
                    # Create comparison dataframe
                    comparison_df = pd.DataFrame(index=sorted(list(all_skills_set)), columns=comparison_data.keys())
                    
                    for candidate, skills in comparison_data.items():
                        for skill in all_skills_set:
                            comparison_df.loc[skill, candidate] = '✓' if skill in skills else ''
                    
                    st.dataframe(comparison_df, use_container_width=True)
        else:
            st.info("Need at least 2 candidates to compare")
    
    # Export functionality
    st.subheader("Export Options")
    col1, col2 = st.columns(2)
    
    with col1:
        try:
            excel_data = export_to_excel(df[display_columns])
            if st.download_button(
                label="📊 Export to Excel",
                data=excel_data,
                file_name="filtered_resumes.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ):
                st.success("Excel export successful!")
        except Exception as e:
            st.error(f"Error exporting to Excel: {e}")
            st.info("Try exporting to CSV instead or contact support if this issue persists.")
    
    with col2:
        try:
            if st.download_button(
                label="📄 Export to CSV",
                data=df[display_columns].to_csv(index=False),
                file_name="filtered_resumes.csv",
                mime="text/csv"
            ):
                st.success("CSV export successful!")
        except Exception as e:
            st.error(f"Error exporting to CSV: {e}")

# No data state
if not uploaded_files and not st.session_state.resume_data:
    st.info("Please upload resume files to get started.")
