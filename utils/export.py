import pandas as pd
import io

def export_to_excel(df):
    try:
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Matching Candidates', index=False)
            
        output.seek(0)
        
        return output.getvalue()
    except Exception as e:
        output = io.BytesIO()
        pd.DataFrame().to_excel(output, index=False)
        output.seek(0)
        return output.getvalue()