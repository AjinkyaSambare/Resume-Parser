import os
import time
import streamlit as st
from utils.gemini_processor import GeminiProcessor

def initialize_processor(secrets_manager):
    """
    Initialize the Gemini processor using the API key from secrets
    
    Args:
        secrets_manager: Instance of SecretsManager
        
    Returns:
        GeminiProcessor: Initialized processor instance
    """
    if st.session_state.gemini_processor is None:
        if st.session_state.gemini_configured:
            try:
                gemini_api_key = secrets_manager.get_secret('api_key', section='gemini')
                st.session_state.gemini_processor = GeminiProcessor(gemini_api_key)
            except Exception as e:
                st.warning(f"Error initializing Google Gemini: {e}")
                st.session_state.gemini_processor = GeminiProcessor("dummy_key")
        else:
            st.warning("Google Gemini API key is not configured in .streamlit/secrets.toml")
            st.session_state.gemini_processor = GeminiProcessor("dummy_key")
    
    return st.session_state.gemini_processor

def process_resumes(file_paths, user_filters, processor):
    """
    Process a batch of resumes with the given filters
    
    Args:
        file_paths: List of paths to resume files
        user_filters: Dictionary of filters to apply
        processor: GeminiProcessor instance
    """
    # Create necessary directories
    os.makedirs('data/uploads', exist_ok=True)
    os.makedirs('data/processed', exist_ok=True)
    
    total_files = len(file_paths)
    batch_size = st.session_state.batch_size
    
    # Create UI elements for progress tracking
    status_container = st.empty()
    progress_bar = st.progress(0)
    file_status = st.empty()
    
    status_container.info(f"Processing {total_files} resumes...")
    
    # Reset processing state
    st.session_state.processing_complete = False
    st.session_state.processing_files = {}
    st.session_state.resume_data = []
    
    # Process files in batches
    for i in range(0, total_files, batch_size):
        batch = file_paths[i:i+batch_size]
        
        # Queue all files in the current batch
        task_ids = []
        for file_path in batch:
            file_name = os.path.basename(file_path)
            task_id = processor.queue_document_for_analysis(file_path, user_filters)
            task_ids.append(task_id)
            st.session_state.processing_files[task_id] = {
                "file_path": file_path,
                "file_name": file_name,
                "status": "queued"
            }
        
        # Wait for the batch to complete
        batch_complete = False
        while not batch_complete:
            for task_id in task_ids:
                result = processor.get_queued_result(task_id)
                
                if result["status"] == "completed":
                    if st.session_state.processing_files[task_id]["status"] != "complete":
                        st.session_state.processing_files[task_id]["status"] = "complete"
                        if result["data"]:
                            st.session_state.resume_data.append(result["data"])
                elif result["status"] == "failed":
                    st.session_state.processing_files[task_id]["status"] = "error"
                    st.session_state.processing_files[task_id]["error"] = result["error"]
            
            completed = sum(1 for task in st.session_state.processing_files.values() 
                          if task["status"] in ["complete", "error"])
            progress = completed / total_files
            progress_bar.progress(progress, text=f"Processed {completed}/{total_files} resumes")
            
            status_text = ""
            for task_id in task_ids:
                task = st.session_state.processing_files[task_id]
                icon = "⏳" if task["status"] == "queued" else "✅" if task["status"] == "complete" else "❌"
                status_text += f"{icon} {task['file_name']}: {task['status'].upper()}\n"
            file_status.code(status_text)
            
            batch_complete = all(st.session_state.processing_files[task_id]["status"] in ["complete", "error"] 
                              for task_id in task_ids)
            
            if not batch_complete:
                time.sleep(1)
    
    st.session_state.processing_complete = True
    
    completed = sum(1 for task in st.session_state.processing_files.values() 
                  if task["status"] == "complete")
    errors = sum(1 for task in st.session_state.processing_files.values() 
               if task["status"] == "error")
    
    progress_bar.progress(1.0, text="Processing complete!")
    
    if errors > 0:
        status_container.warning(f"Processed {completed}/{total_files} resumes. {errors} had errors.")
    else:
        status_container.success(f"Successfully processed all {total_files} resumes!")
    
    filter_and_sort_matches(user_filters)

def filter_and_sort_matches(user_filters):
    """
    Filter and sort the processed resume data using the provided filters
    (now using Gemini directly in each document instead of a separate filter step)
    
    Args:
        user_filters: Dictionary of filters to apply
    """
    # With Gemini processing, filtering happens directly during document processing
    # Just sort by match score now
    st.session_state.matches = st.session_state.resume_data
    
    # Sort by match score in descending order
    st.session_state.matches.sort(key=lambda x: x.get('match_score', 0), reverse=True)