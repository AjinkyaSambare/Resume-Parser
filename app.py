import streamlit as st
from utils.file_handler import save_uploaded_files
from components.initialization import initialize_app_state, check_api_configuration
from components.processor import initialize_processor, process_resumes, update_processing_status
from components.results import display_results
from components.filter import filter_resumes_with_nlp, simple_keyword_filter
import os

# Initialize app state
secrets_manager = initialize_app_state()

# Configure page settings
st.set_page_config(
    page_title="ResumeParser",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for styling - Updated for modern UI
st.markdown("""
<style>
    /* Global styles */
    body {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        background-color: #ffffff;
        color: #333333;
    }
    
    /* Main container */
    .main-container {
        max-width: 1000px;
        margin: 0 auto;
        padding: 2rem 1rem;
    }
    
    /* Header styles */
    .logo-container {
        text-align: center;
        margin-bottom: 0.5rem;
    }
    
    .main-title {
        text-align: center;
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.25rem;
        color: #1a1a1a;
    }
    
    .subtitle {
        text-align: center;
        color: #666666;
        font-size: 1rem;
        margin-bottom: 2rem;
    }
    
    /* Action labels (top non-functional elements) */
    .action-labels {
        display: flex;
        justify-content: space-between;
        margin-bottom: 2rem;
        padding: 0 1rem;
    }
    
    .label-item {
        display: flex;
        align-items: center;
        padding: 0.75rem 1.5rem;
        background-color: #fafafa;
        border-radius: 50px;
        font-weight: 500;
        color: #333333;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    
    .label-icon {
        margin-right: 0.5rem;
    }
    
    /* Upload section */
    .upload-section {
        border: 2px dashed #e0e0e0;
        border-radius: 10px;
        padding: 2.5rem;
        margin-bottom: 1.5rem;
        text-align: center;
        background-color: #fafafa;
    }
    
    .upload-icon {
        font-size: 2rem;
        margin-bottom: 1rem;
        color: #888888;
    }
    
    .upload-title {
        font-size: 1.25rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
        color: #333333;
    }
    
    .upload-subtitle {
        color: #666666;
        margin-bottom: 1rem;
    }
    
    .file-types {
        color: #888888;
        font-size: 0.85rem;
        margin-top: 0.5rem;
    }
    
    /* Divider */
    .divider {
        display: flex;
        align-items: center;
        text-align: center;
        margin: 1.5rem 0;
        color: #888888;
    }
    
    .divider::before,
    .divider::after {
        content: '';
        flex: 1;
        border-bottom: 1px solid #e0e0e0;
    }
    
    .divider-text {
        padding: 0 1rem;
    }
    
    /* Sample button */
    .sample-button {
        width: 100%;
        padding: 0.75rem;
        background-color: #fafafa;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        font-weight: 500;
        color: #555555;
    }
    
    /* Filter input */
    .filter-container {
        margin-top: 1.5rem;
        margin-bottom: 0.5rem;
    }
    
    .filter-input {
        border-radius: 8px;
        border: 1px solid #e0e0e0;
        padding: 0.75rem 1rem;
        width: 100%;
        font-size: 1rem;
    }
    
    .filter-hint {
        color: #888888;
        font-size: 0.85rem;
        margin-top: 0.5rem;
    }
    
    /* Results section */
    .results-container {
        margin-top: 2rem;
    }
    
    .results-header-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1.5rem;
        padding: 0;
    }
    
    .results-title {
        font-size: 2rem;
        font-weight: 600;
        margin: 0;
        color: #1a1a1a;
    }
    
    .results-export-button {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 4px;
        padding: 8px 16px;
        display: flex;
        align-items: center;
        gap: 8px;
        font-weight: 500;
        color: #495057;
    }
    
    /* Data table container */
    .data-table-container {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        overflow: hidden;
        margin-bottom: 2rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    
    /* Button styles */
    .custom-button {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        padding: 0.5rem 1.25rem;
        background-color: #f5f5f5;
        border: 1px solid #e0e0e0;
        border-radius: 50px;
        font-weight: 500;
        color: #333333;
        text-decoration: none;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    
    .custom-button:hover {
        background-color: #eeeeee;
    }
    
    .custom-button.primary {
        background-color: #4F46E5;
        color: white;
        border: none;
    }
    
    .custom-button.primary:hover {
        background-color: #4338CA;
    }
    
    /* Hide Streamlit components */
    #MainMenu, footer, header {
        visibility: hidden;
    }
    
    /* Override Streamlit styles */
    .stApp {
        max-width: 100%;
    }
    
    .block-container {
        max-width: 1000px;
        padding-top: 1rem;
        padding-right: 1rem;
        padding-left: 1rem;
        padding-bottom: 1rem;
    }
    
    /* Make file uploader cleaner */
    .stFileUploader > div > button {
        display: none;
    }
    
    .uploadedFile {
        display: none;
    }
    
    /* Input field styling */
    .stTextInput > div > div {
        background-color: white;
        border-radius: 8px;
    }
    
    /* Style the table */
    .stDataFrame {
        border: none !important;
    }
    
    /* Fix for button styling */
    .stButton > button {
        border-radius: 4px;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)

# Main container
st.markdown('<div class="main-container">', unsafe_allow_html=True)

# Logo and title section
st.markdown('<div class="logo-container"><span style="font-size: 2.5rem;"></span></div>', unsafe_allow_html=True)
st.markdown('<h1 class="main-title">ResumeParser</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Upload, filter, and analyze resumes with natural language processing</p>', unsafe_allow_html=True)

# Top section labels (non-functional)
st.markdown('<div class="action-labels">', unsafe_allow_html=True)
col1, col2 = st.columns([1, 1])
with col1:
    st.markdown('<div class="label-item"><span class="label-icon">🔍</span> Filter with natural language</div>', unsafe_allow_html=True)
with col2:
    st.markdown('<div class="label-item"><span class="label-icon">⬇️</span> Export to Excel</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# Upload section
st.markdown('<div class="">', unsafe_allow_html=True)
st.markdown('<div class="upload-icon"></div>', unsafe_allow_html=True)
st.markdown('<h3 class="upload-title">Upload your resumes</h3>', unsafe_allow_html=True)
st.markdown('<p class="upload-subtitle">Drag & drop your files here or click to browse</p>', unsafe_allow_html=True)

uploaded_files = st.file_uploader(
    label="Upload resumes",
    accept_multiple_files=True,
    type=['pdf', 'doc', 'docx', 'txt'],
    label_visibility="collapsed"
)

st.markdown('<p class="file-types">Supports PDF, DOC, DOCX, TXT</p>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# OR Divider
st.markdown('<div class="divider"><span class="divider-text">OR</span></div>', unsafe_allow_html=True)

# Sample resumes button
sample_clicked = st.button("📋 Load sample resumes", use_container_width=True, key="sample_btn")

# Filter input
st.markdown('<div class="filter-container">', unsafe_allow_html=True)
query = st.text_input(
    "Filter resumes with natural language...",
    placeholder="(e.g., 'React developers with 3+ years experience')",
)
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown('', unsafe_allow_html=True)
with col2:
    filter_button = st.button("🔍 Filter with natural language", key="filter_btn", help="Process and filter uploaded resumes")
st.markdown('</div>', unsafe_allow_html=True)

# Clear filtered results if query is cleared
if not query and 'filtered_matches' in st.session_state:
    del st.session_state.filtered_matches

# Process Files Logic
if uploaded_files:
    if 'pending_files' not in st.session_state:
        st.session_state.pending_files = []
    
    # Store references to files but don't process them yet
    for file in uploaded_files:
        if file.name not in st.session_state.pending_files:
            st.session_state.pending_files.append(file.name)
    
    # Show message about using filters
    if not query:
        st.info(f"📝 {len(uploaded_files)} files ready. Enter filtering criteria above and click 'Filter with natural language' to process.")

# Sample data loading
if sample_clicked:
    try:
        # Check if we have a samples directory
        sample_dir = os.path.join("data", "samples")
        if not os.path.exists(sample_dir):
            os.makedirs(sample_dir, exist_ok=True)
            st.warning("Sample directory created but no sample files found. Please add some files to the data/samples directory.")
        else:
            sample_files = [f for f in os.listdir(sample_dir) if f.endswith(('.pdf', '.docx', '.doc', '.txt'))]
            if sample_files:
                # Add sample files to pending_files instead of processing them immediately
                if 'pending_files' not in st.session_state:
                    st.session_state.pending_files = []
                
                for file in sample_files:
                    if file not in st.session_state.pending_files:
                        st.session_state.pending_files.append(file)
                
                # Store sample file paths for later processing
                st.session_state.sample_file_paths = [os.path.join(sample_dir, f) for f in sample_files]
                
                # Inform user about next steps
                st.success(f"Loaded {len(sample_files)} sample resumes")
                st.info("Enter filtering criteria above and click 'Filter with natural language' to search through the sample resumes.")
            else:
                st.warning("No sample files found. Please add some files to the data/samples directory.")
    except Exception as e:
        st.error(f"Error loading sample files: {e}")

# Apply filtering if requested
if filter_button and query:
    try:
        files_to_process = False
        file_paths = []
        
        # Check if we need to process uploaded files
        if uploaded_files and 'pending_files' in st.session_state and st.session_state.pending_files:
            file_paths.extend(save_uploaded_files(uploaded_files))
            files_to_process = True
        
        # Check if we need to process sample files
        if 'sample_file_paths' in st.session_state and st.session_state.sample_file_paths:
            file_paths.extend(st.session_state.sample_file_paths)
            # Clear sample file paths to avoid duplicate processing
            st.session_state.sample_file_paths = []
            files_to_process = True
        
        # Process files if needed
        if files_to_process:
            with st.spinner("Processing resumes before filtering..."):
                processor = initialize_processor(secrets_manager)
                
                # Default filters initially
                user_filters = {
                    'skills': [],
                    'min_experience': 0,
                    'education_level': "Any",
                    'location': "",
                    'custom_filters': {}
                }
                
                st.session_state.user_filters = user_filters
                process_resumes(file_paths, user_filters, processor)
                
                # Mark files as processed
                st.session_state.pending_files = []
                if 'processed_files' not in st.session_state:
                    st.session_state.processed_files = []
                if uploaded_files:
                    st.session_state.processed_files.extend([file.name for file in uploaded_files])
        
        # Now apply filters if we have processed resumes
        if 'matches' in st.session_state and st.session_state.matches:
            with st.spinner("Filtering resumes..."):
                processor = st.session_state.gemini_processor if 'gemini_processor' in st.session_state and st.session_state.gemini_processor is not None else None
                try:
                    # First try with AI-based filtering
                    if processor:
                        filtered_results = filter_resumes_with_nlp(query, processor, st.session_state.matches)
                        st.session_state.filtered_matches = filtered_results
                        st.success(f"Found {len(filtered_results)} matching resumes")
                    else:
                        # Fallback to simple keyword filtering
                        st.warning("AI processor not available. Using basic keyword filtering.")
                        filtered_results = simple_keyword_filter(query, st.session_state.matches)
                        st.session_state.filtered_matches = filtered_results
                        st.success(f"Found {len(filtered_results)} matching resumes with basic filtering")
                except Exception as e:
                    # Handle any exceptions during filtering
                    st.error(f"Error during advanced filtering: {str(e)}")
                    st.warning("Falling back to basic keyword search...")
                    filtered_results = simple_keyword_filter(query, st.session_state.matches)
                    st.session_state.filtered_matches = filtered_results
                    if filtered_results:
                        st.success(f"Found {len(filtered_results)} matching resumes with basic filtering")
                    else:
                        st.warning("No matching resumes found")
        else:
            st.warning("No resumes have been processed yet. Please upload resumes and try again.")
    except Exception as e:
        st.error(f"Error filtering resumes: {e}")

# Results section with export button
if 'filtered_matches' in st.session_state and st.session_state.filtered_matches:
    # Results header with export button - Outside the results container
    st.markdown('<div class="results-container">', unsafe_allow_html=True)
    st.markdown('<div class="results-header-container">', unsafe_allow_html=True)
    col1, col2 = st.columns([6, 1])
    with col1:
        st.markdown('<h2 class="results-title">Results</h2>', unsafe_allow_html=True)
    with col2:
        export_button = st.button(" Export to Excel", key="export_btn", help="Export filtered results to Excel")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Data table in its own container
    st.markdown('<div class="data-table-container">', unsafe_allow_html=True)
    # Temporarily swap the matches with filtered matches for display
    original_matches = st.session_state.matches
    st.session_state.matches = st.session_state.filtered_matches
    display_results()
    # Restore original matches
    st.session_state.matches = original_matches
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Export functionality
    if export_button:
        data_to_export = st.session_state.filtered_matches
        if data_to_export:
            try:
                from utils.export import export_to_excel
                import pandas as pd
                
                df = pd.DataFrame(data_to_export)
                columns_to_export = st.session_state.display_columns if 'display_columns' in st.session_state else df.columns
                
                excel_data = export_to_excel(df[columns_to_export])
                st.download_button(
                    label="Download Excel File",
                    data=excel_data,
                    file_name="parsed_resumes.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
                st.success("Excel file ready for download!")
            except Exception as e:
                st.error(f"Error exporting data: {e}")
        else:
            st.warning("No resume data available to export. Please upload and filter resumes first.")
    
    st.markdown('</div>', unsafe_allow_html=True)
elif query and filter_button and not st.session_state.get('filtered_matches', []):
    # We tried filtering but didn't find any matches
    st.markdown('<div class="results-container">', unsafe_allow_html=True)
    st.warning(f"No resumes found matching '{query}'")
    st.markdown('</div>', unsafe_allow_html=True)

# Check API configuration in background
check_api_configuration()

# Close main container
st.markdown('</div>', unsafe_allow_html=True)