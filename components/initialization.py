import streamlit as st
from utils.secrets_manager import SecretsManager

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    st.error("Google Generative AI package is not installed. Please run: pip install google-generativeai")

def initialize_app_state():
    """Initialize application state and return the secrets manager"""
    secrets_manager = SecretsManager()
    
    # Initialize session state variables if they don't exist
    if 'resume_data' not in st.session_state:
        st.session_state.resume_data = []
    if 'matches' not in st.session_state:
        st.session_state.matches = []
    if 'gemini_processor' not in st.session_state:
        st.session_state.gemini_processor = None
    if 'gemini_configured' not in st.session_state:
        if GEMINI_AVAILABLE:
            st.session_state.gemini_configured = secrets_manager.has_secrets(section='gemini')
        else:
            st.session_state.gemini_configured = False
    if 'batch_size' not in st.session_state:
        st.session_state.batch_size = 5
    if 'processing_files' not in st.session_state:
        st.session_state.processing_files = {}
    if 'processing_complete' not in st.session_state:
        st.session_state.processing_complete = False
    if 'filter_query' not in st.session_state:
        st.session_state.filter_query = ""
    
    # Use Gemini as the AI provider
    st.session_state.ai_provider = 'gemini'
    
    # Define column name mapping - mapping original column names to display names
    if 'column_mapping' not in st.session_state:
        st.session_state.column_mapping = {
            'filename': 'Resume Filename',
            'name': 'Applicant Name',
            'email': 'Applicant Email',
            'phone': 'Applicant Phone',
            'education': 'Applicant Education',
            'experience': 'Applicant Experience',
            'skills': 'Applicant Skills',
            'match_score': 'Applicant Match Score'
        }
    
    # Default display columns for the results table (using original column names)
    if 'display_columns' not in st.session_state:
        st.session_state.display_columns = ['filename', 'name', 'email', 'phone', 'education', 'experience', 'skills', 'match_score']
    
    # Track custom columns
    if 'custom_columns' not in st.session_state:
        st.session_state.custom_columns = []
    
    # Track custom column prompts
    if 'custom_column_prompts' not in st.session_state:
        st.session_state.custom_column_prompts = {}
    
    return secrets_manager

def check_api_configuration():
    """Check if the Gemini API key is properly configured"""
    if not GEMINI_AVAILABLE:
        st.error("Google Generative AI package is not installed. This application requires it for processing resumes.")
        st.info("Please install the package using: pip install google-generativeai")
        return False
        
    if not st.session_state.gemini_configured:
        st.warning("Gemini API key is not configured. The application requires this for resume processing.")
        st.info("Please add your Gemini API key in .streamlit/secrets.toml")
        return False
        
    return True