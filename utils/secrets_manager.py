import streamlit as st
from pathlib import Path

class SecretsManager:
    
    def __init__(self):
        self.sections = {}
        self.load_secrets()
    
    def load_secrets(self):
        try:
            if hasattr(st, 'secrets'):
                if 'gemini' in st.secrets:
                    self.sections['gemini'] = st.secrets['gemini']
            else:
                self._ensure_local_secrets_file()
                
                try:
                    if 'gemini' in st.secrets:
                        self.sections['gemini'] = st.secrets['gemini']
                except (KeyError, AttributeError):
                    st.warning("Gemini API credentials not found in secrets.")
                    self.sections = {}
        except Exception as e:
            st.error(f"Error loading secrets: {e}")
            self.sections = {}
    
    def get_secret(self, key, default=None, section='gemini'):
        if section in self.sections:
            return self.sections[section].get(key, default)
        return default
    
    def has_secrets(self, section='gemini'):
        required_keys = ['api_key']
        section_data = self.sections.get(section, {})
        
        return all(key in section_data 
                  and section_data[key] 
                  and section_data[key] != "your_gemini_api_key_here" 
                  for key in required_keys)
    
    def has_secret(self, key, section='gemini'):
        if section in self.sections:
            return (key in self.sections[section] 
                   and self.sections[section][key] 
                   and self.sections[section][key] != "your_gemini_api_key_here")
        return False
    
    def _ensure_local_secrets_file(self):
        secrets_dir = Path('.streamlit')
        secrets_file = secrets_dir / 'secrets.toml'
        
        if not secrets_file.exists():
            secrets_dir.mkdir(exist_ok=True)
            
            with open(secrets_file, 'w') as f:
                f.write("""
# Google Gemini API credentials
[gemini]
api_key = "your_gemini_api_key_here"
                """)
            
            st.warning("""
            A template secrets.toml file has been created in the .streamlit directory.
            Please edit this file to add your Gemini API key.
            """)