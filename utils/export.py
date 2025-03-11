"""
Export functions for resume data
"""

import pandas as pd
import io

def export_to_excel(df):
    """
    Export a DataFrame to Excel file
    
    Parameters:
    - df: Pandas DataFrame to export
    
    Returns:
    - Excel file as bytes object
    """
    try:
        # Create a buffer
        output = io.BytesIO()
        
        # Create Excel writer
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Write DataFrame to Excel
            df.to_excel(writer, sheet_name='Matching Candidates', index=False)
            
        # Reset pointer to start of file
        output.seek(0)
        
        return output.getvalue()
    except Exception as e:
        # Return empty Excel file if error occurs
        output = io.BytesIO()
        pd.DataFrame().to_excel(output, index=False)
        output.seek(0)
        return output.getvalue()
