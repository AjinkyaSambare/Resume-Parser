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
    # Create a buffer
    output = io.BytesIO()
    
    # Create Excel writer
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # Write DataFrame to Excel
        df.to_excel(writer, sheet_name='Filtered Resumes', index=False)
        
        # Get the worksheet
        worksheet = writer.sheets['Filtered Resumes']
        
        # Set column widths
        for i, col in enumerate(df.columns):
            # Set width based on column name length and content
            max_len = max(
                df[col].astype(str).map(len).max(),  # Max content length
                len(str(col))  # Column name length
            ) + 2  # Add a little extra space
            
            # Set max width to avoid extremely wide columns
            col_width = min(max_len, 50)
            
            # Set column width
            worksheet.set_column(i, i, col_width)
        
        # Add filtering capability
        worksheet.autofilter(0, 0, len(df), len(df.columns) - 1)
    
    # Reset pointer to start of file
    output.seek(0)
    
    return output.getvalue()

def export_to_csv(df):
    """
    Export a DataFrame to CSV file
    
    Parameters:
    - df: Pandas DataFrame to export
    
    Returns:
    - CSV file as string
    """
    # Create a buffer
    output = io.StringIO()
    
    # Write DataFrame to CSV
    df.to_csv(output, index=False)
    
    # Get CSV content
    csv_content = output.getvalue()
    
    return csv_content