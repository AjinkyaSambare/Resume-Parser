import os
import time
import streamlit as st
from utils.gemini_processor import GeminiProcessor
from utils.filters import filter_resumes

def initialize_processor(secrets_manager):
    if st.session_state.gemini_processor is None:
        if st.session_state.gemini_configured:
            try:
                gemini_api_key = secrets_manager.get_secret('api_key', section='gemini')
                st.session_state.gemini_processor = GeminiProcessor(gemini_api_key)
            except Exception as e:
                st.warning(f"Error initializing Google Gemini: {e}")
                st.info("Using basic fallback functionality without AI.")
                st.session_state.gemini_processor = GeminiProcessor("dummy_key")
        else:
            st.warning("Google Gemini API key is not configured.")
            st.info("Using basic fallback functionality without AI.")
            st.session_state.gemini_processor = GeminiProcessor("dummy_key")
    
    return st.session_state.gemini_processor

def process_resumes(file_paths, user_filters, processor):
    os.makedirs('data/uploads', exist_ok=True)
    os.makedirs('data/processed', exist_ok=True)
    
    total_files = len(file_paths)
    batch_size = st.session_state.batch_size
    
    status_container = st.empty()
    progress_bar = st.progress(0)
    file_status = st.empty()
    
    status_container.info(f"Processing {total_files} resumes...")
    
    st.session_state.processing_complete = False
    st.session_state.processing_files = {}
    st.session_state.resume_data = []
    
    for i in range(0, total_files, batch_size):
        batch = file_paths[i:i+batch_size]
        
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

def update_processing_status(processor):
    if processor:
        task_statuses = processor.get_all_task_statuses()
        
        for task_id, status in task_statuses.items():
            if task_id in st.session_state.processing_files:
                prev_status = st.session_state.processing_files[task_id]["status"]
                if status == "completed" and prev_status != "complete":
                    result = processor.get_queued_result(task_id)
                    st.session_state.processing_files[task_id]["status"] = "complete"
                    if result["data"] and result["data"] not in st.session_state.resume_data:
                        st.session_state.resume_data.append(result["data"])
                elif status == "failed" and prev_status != "error":
                    result = processor.get_queued_result(task_id)
                    st.session_state.processing_files[task_id]["status"] = "error"
                    st.session_state.processing_files[task_id]["error"] = result.get("error", "Unknown error")
    
    total_files = len(st.session_state.processing_files)
    completed = sum(1 for task in st.session_state.processing_files.values() 
                  if task["status"] in ["complete", "error"])
    progress = completed / total_files if total_files > 0 else 0
    
    st.info(f"Resume processing in progress: {completed}/{total_files} complete")
    st.progress(progress)
    
    status_text = ""
    for task_id, task in st.session_state.processing_files.items():
        icon = "⏳" if task["status"] == "queued" else "✅" if task["status"] == "complete" else "❌"
        status_text += f"{icon} {task['file_name']}: {task['status'].upper()}\n"
    st.code(status_text)
    
    if completed == total_files:
        st.session_state.processing_complete = True
        st.success("Processing complete!")
        
        if 'user_filters' in st.session_state:
            filters_to_use = st.session_state.user_filters
        else:
            filters_to_use = {
                'skills': [],
                'min_experience': 0,
                'education_level': 'Any',
                'location': '',
                'custom_filters': {}
            }
        
        filter_and_sort_matches(filters_to_use)

def filter_and_sort_matches(user_filters):
    st.session_state.matches = filter_resumes(
        st.session_state.resume_data,
        skills=user_filters.get('skills', []),
        min_experience=user_filters.get('min_experience', 0),
        education_level=user_filters.get('education_level', 'Any'),
        location=user_filters.get('location', ''),
        custom_filters=user_filters.get('custom_filters', {})
    )
    
    st.session_state.matches.sort(key=lambda x: x.get('match_score', 0), reverse=True)