import pandas as pd
import io

def export_to_excel(df):
    """
    Export DataFrame to Excel file
    
    Args:
        df: Pandas DataFrame to export
        
    Returns:
        BytesIO object containing the Excel file
    """
    try:
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Matching Candidates', index=False)
            
        output.seek(0)
        
        return output.getvalue()
    except Exception as e:
        # Return empty Excel file on error
        output = io.BytesIO()
        pd.DataFrame().to_excel(output, index=False)
        output.seek(0)
        return output.getvalue()