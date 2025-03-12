import streamlit as st
from utils.secrets_manager import SecretsManager

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

def initialize_app_state():
    secrets_manager = SecretsManager()
    
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
    
    st.session_state.ai_provider = 'gemini'
    
    if 'display_columns' not in st.session_state:
        st.session_state.display_columns = ['filename', 'name', 'email', 'phone', 'education', 'experience', 'skills', 'match_score']
    
    # Ensure custom columns are tracked
    if 'custom_columns' not in st.session_state:
        st.session_state.custom_columns = []
    
    return secrets_manager

def check_api_configuration():
    """Check if the API is properly configured and available"""
    if not st.session_state.gemini_configured:
        # Instead of showing a warning, we'll just log this in the session state
        st.session_state.api_warning = """
        Gemini API is not configured. The application will use basic keyword extraction instead of AI.
        Please add your Gemini API key for full functionality.
        """
    
    if not GEMINI_AVAILABLE:
        # Instead of showing a warning, we'll just log this in the session state
        st.session_state.package_warning = """
        The Google Generative AI package is not installed.
        The application will fall back to limited functionality using basic keyword extraction.
        """
    
    return True