import pandas as pd
import streamlit as st
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
    
    # Custom Column Adder
    with st.expander("➕ Add Custom Column Name"):
        # Two separate fields: one for column name and one for the prompt
        column_name = st.text_input(
            "Enter column name:",
            placeholder="e.g., Python Experience"
        )
        
        column_prompt = st.text_input(
            "Enter prompt for this column:",
            placeholder="e.g., Extract years of Python programming experience from this resume"
        )
        
        # Add column button
        add_column_button = st.button("Add Column")
        
    # Process when button is clicked
    if add_column_button and column_name and column_prompt:
        with st.spinner(f"Extracting {column_name}..."):
            extract_custom_column(column_name, column_prompt)
    elif add_column_button and not (column_name and column_prompt):
        st.warning("Please enter both a column name and a prompt.")
    
    # Display results table with renamed columns
    with st.container():
        if 'display_columns' in st.session_state:
            # Create a copy of the dataframe with only the columns to display
            display_df = df[st.session_state.display_columns].copy()
            
            # Rename columns that exist in the mapping
            if 'column_mapping' in st.session_state:
                for old_name, new_name in st.session_state.column_mapping.items():
                    if old_name in display_df.columns:
                        display_df.rename(columns={old_name: new_name}, inplace=True)
            
            st.dataframe(display_df, use_container_width=True, height=600)
        else:
            st.dataframe(df, use_container_width=True, height=600)
    
    # Return Excel data if export only
    if export_only:
        try:
            columns_to_export = st.session_state.display_columns if 'display_columns' in st.session_state else df.columns
            
            # Create a copy of the dataframe with the columns to export
            export_df = df[columns_to_export].copy()
            
            # Rename columns that exist in the mapping
            if 'column_mapping' in st.session_state:
                for old_name, new_name in st.session_state.column_mapping.items():
                    if old_name in export_df.columns:
                        export_df.rename(columns={old_name: new_name}, inplace=True)
            
            excel_data = export_to_excel(export_df)
            return excel_data
        except Exception as e:
            st.error(f"Error preparing Excel export: {e}")
            return None

def extract_custom_column(column_name, column_prompt):
    """
    Extract custom information from resumes using Gemini
    
    Args:
        column_name (str): Name of the new column to display
        column_prompt (str): Prompt to extract information with
    """
    processor = st.session_state.gemini_processor
    
    if not processor:
        st.error("No AI processor available")
        return
    
    for resume in st.session_state.matches:
        file_path = resume.get('file_path', "")
        try:
            text = get_text_from_file(file_path)
            
            custom_prompt = f"""You are extracting specific information from a resume.

TASK: {column_prompt}

Resume text:
{text[:10000]}

Provide ONLY the requested information as plain text. Be precise and thorough.
If the information cannot be found, state "Not found in resume".
Do not include explanations, analysis, or any additional text."""
            
            result = processor._call_gemini_with_retry(custom_prompt)
            resume[column_name] = result.strip()
                
        except Exception as e:
            resume[column_name] = f"Error processing: {str(e)[:50]}"
    
    if column_name not in st.session_state.display_columns:
        st.session_state.display_columns.append(column_name)
    
    # Add custom column to column mapping with same name (no rename)
    if 'column_mapping' in st.session_state and column_name not in st.session_state.column_mapping:
        st.session_state.column_mapping[column_name] = column_name
    
    # Track custom columns for future use
    if 'custom_columns' not in st.session_state:
        st.session_state.custom_columns = []
    if column_name not in st.session_state.custom_columns:
        st.session_state.custom_columns.append(column_name)
    
    st.success(f"Added column: {column_name}")
    st.rerun()