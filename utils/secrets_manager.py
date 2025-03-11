import streamlit as st
import os
import json
from pathlib import Path

class SecretsManager:
    """
    Class to manage secrets for the application
    Supports both local development and Streamlit Cloud deployment
    """
    
    def __init__(self):
        # Initialize secrets dictionary
        self.secrets = {}
        self.load_secrets()
    
    def load_secrets(self):
        """
        Load secrets from Streamlit secrets or local .streamlit/secrets.toml
        """
        try:
            # Try to get secrets from Streamlit
            if hasattr(st, 'secrets') and 'azure_openai' in st.secrets:
                self.secrets = st.secrets['azure_openai']
            else:
                # For local development, create a sample secrets file if it doesn't exist
                self._ensure_local_secrets_file()
                
                # Try to load from the local secrets file
                try:
                    self.secrets = st.secrets['azure_openai']
                except (KeyError, AttributeError):
                    st.warning("Azure OpenAI API credentials not found in secrets.")
                    self.secrets = {}
        except Exception as e:
            st.error(f"Error loading secrets: {e}")
            self.secrets = {}
    
    def get_secret(self, key, default=None):
        """
        Get a secret value by key
        
        Parameters:
        - key: The secret key to retrieve
        - default: Default value if key doesn't exist
        
        Returns:
        - The secret value or default
        """
        return self.secrets.get(key, default)
    
    def has_secrets(self):
        """
        Check if required secrets are available
        
        Returns:
        - True if all required secrets are available, False otherwise
        """
        required_keys = ['api_key', 'endpoint']
        return all(key in self.secrets and self.secrets[key] and self.secrets[key] != "your_api_key_here" for key in required_keys)
    
    def _ensure_local_secrets_file(self):
        """
        Create a sample secrets.toml file for local development if it doesn't exist
        """
        secrets_dir = Path('.streamlit')
        secrets_file = secrets_dir / 'secrets.toml'
        
        if not secrets_file.exists():
            # Create directory if it doesn't exist
            secrets_dir.mkdir(exist_ok=True)
            
            # Create a template secrets file
            with open(secrets_file, 'w') as f:
                f.write("""
# Azure OpenAI API credentials
[azure_openai]
api_key = "your_api_key_here"
endpoint = "https://access-01.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2024-08-01-preview"
                """)
            
            st.warning("""
            A template secrets.toml file has been created in the .streamlit directory.
            Please edit this file to add your Azure OpenAI API credentials.
            """)
