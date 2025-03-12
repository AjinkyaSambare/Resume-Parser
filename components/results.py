import pandas as pd
import streamlit as st
import plotly.express as px
from utils.export import export_to_excel
from utils.file_handler import get_text_from_file

def display_results(export_only=False):
    """Display the results of resume parsing and analysis
    
    Args:
        export_only (bool): If True, only show export options without displaying the data
    """
    if 'matches' not in st.session_state or not st.session_state.matches:
        return
        
    # Create dataframe from matches
    df = pd.DataFrame(st.session_state.matches)
    for col in st.session_state.display_columns:
        if col not in df.columns:
            df[col] = ""
    
    # Custom Column Adder - Restored functionality
    with st.expander("➕ Add Custom Column Name"):
    # Input field on full width
        new_column = st.text_input(
            "What information would you like to extract?",
            placeholder="e.g., Years of Python experience"
        )
        
        # Add column button
        add_column_button = st.button("Add Column")
        
    # Conditional processing when button is clicked
    if add_column_button and new_column:
        with st.spinner(f"Extracting {new_column}..."):
            extract_custom_column(new_column)
    
    # Display results table with more height to use full screen space
    # Use a container to ensure it respects the margins
    with st.container():
        if 'display_columns' in st.session_state:
            st.dataframe(df[st.session_state.display_columns], use_container_width=True, height=600)
        else:
            st.dataframe(df, use_container_width=True, height=600)
    
   
    if export_only:
        try:
            columns_to_export = st.session_state.display_columns if 'display_columns' in st.session_state else df.columns
            excel_data = export_to_excel(df[columns_to_export])
            return excel_data
        except Exception as e:
            st.error(f"Error preparing Excel export: {e}")
            return None

def extract_custom_column(new_column):
    processor = st.session_state.gemini_processor if hasattr(st.session_state, 'gemini_processor') else None
    
    if not processor:
        st.error("No AI processor available")
        st.warning("Using basic extraction method instead.")
        for resume in st.session_state.matches:
            resume[new_column] = "Not available (AI processor required)"
        
        if new_column not in st.session_state.display_columns:
            st.session_state.display_columns.append(new_column)
        
        st.success(f"Added column: {new_column} (with limited functionality)")
        st.rerun()
        return
    
    for resume in st.session_state.matches:
        file_path = resume.get('file_path', "")
        try:
            text = get_text_from_file(file_path)
            
            custom_prompt = f"""You are extracting specific information from a resume.

TASK: {new_column}

Resume text:
{text[:10000]}

Provide ONLY the requested information as plain text. Be precise and thorough.
If the information cannot be found, state "Not found in resume".
Do not include explanations, analysis, or any additional text."""
            
            extract_with_gemini(resume, custom_prompt, processor, new_column)
                
        except Exception as e:
            resume[new_column] = f"Error processing: {str(e)[:50]}"
    
    if new_column not in st.session_state.display_columns:
        st.session_state.display_columns.append(new_column)
    
    # Track custom columns for future use
    if 'custom_columns' not in st.session_state:
        st.session_state.custom_columns = []
    if new_column not in st.session_state.custom_columns:
        st.session_state.custom_columns.append(new_column)
    
    st.success(f"Added column: {new_column}")
    st.rerun()

def extract_with_gemini(resume, custom_prompt, processor, new_column):
    try:
        result = processor._call_gemini_with_retry(custom_prompt)
        resume[new_column] = result.strip()
    except Exception as e:
        resume[new_column] = f"Error: {str(e)[:50]}"


