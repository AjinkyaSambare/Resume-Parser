import streamlit as st
import os

def render_upload_section():
    """
    Render the file upload section with drag & drop functionality
    
    Returns:
        list: List of uploaded file objects
    """
    uploaded_files = st.file_uploader(
        "Upload Resumes",
        accept_multiple_files=True,
        type=['pdf', 'doc', 'docx', 'txt'],
    )
    
    return uploaded_files

def render_sample_data_button():
    """
    Render button to load sample resume data
    
    Returns:
        bool: True if the button was clicked
    """
    load_samples = st.button("📄 Load sample resumes", use_container_width=True)
    
    if load_samples:
        # Logic to load sample resumes
        st.info("Loading sample resumes...")
        try:
            sample_dir = os.path.join("data", "samples")
            if os.path.exists(sample_dir):
                sample_files = [f for f in os.listdir(sample_dir) if f.endswith(('.pdf', '.docx'))]
                if sample_files:
                    st.session_state.sample_files = [os.path.join(sample_dir, f) for f in sample_files]
                    st.success(f"Loaded {len(sample_files)} sample resumes")
                else:
                    st.warning("No sample resume files found in data/samples directory")
            else:
                st.warning("Sample directory not found")
        except Exception as e:
            st.error(f"Error loading sample files: {e}")
    
    return load_samples

def render_filter_section():
    """
    Render the filter section with natural language search capabilities
    
    Returns:
        tuple: (query, filter_button) where query is the text input and filter_button is a boolean
    """
    query = st.text_input(
        "Filter resumes with natural language",
        placeholder="(e.g., 'React developers with 3+ years experience')"
    )
    
    col1, col2 = st.columns(2)
    with col1:
        filter_button = st.button("🔍 Filter with natural language", use_container_width=True)
    with col2:
        export_button = st.button("⬇️ Export to Excel", use_container_width=True)
    
    # Suggested filter queries
    st.markdown(
        '<p style="color: #666; font-size: 0.9rem;">Try "Java developers", "5+ years experience", or "Master\'s degree in Computer Science"</p>',
        unsafe_allow_html=True
    )
    
    return query, filter_button, export_button
