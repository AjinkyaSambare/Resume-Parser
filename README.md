# AI-Powered Resume Matcher with Azure OpenAI Integration

A Streamlit application that finds the perfect candidates from your resume collection using Azure OpenAI's GPT-4o model.

## Features

- **Simple Workflow**: Upload resumes, describe what you're looking for, and get results in one step
- **Natural Language Search**: Use everyday language to describe your ideal candidate
- **Smart Matching**: AI-powered matching provides scores and detailed explanations
- **Custom Columns**: Add any information you need with a simple prompt
- **Excel Export**: Export your results with one click

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Azure OpenAI API key

### Setup

1. Clone the repository or download the source code:

```bash
git clone <repository-url>
cd resume-matcher
```

2. Create a virtual environment (optional but recommended):

```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

3. Install the required dependencies:

```bash
pip install -r requirements.txt
```

4. Configure Azure OpenAI:

Create a `.streamlit/secrets.toml` file with your Azure OpenAI credentials:

```toml
# Azure OpenAI API credentials
[azure_openai]
api_key = "your_api_key_here"
endpoint = "https://access-01.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2024-08-01-preview"
```

## Usage

1. Start the Streamlit application:

```bash
streamlit run app.py
```

2. Access the application in your web browser (typically at http://localhost:8501)

3. Upload your resume files using the file uploader

4. Describe what you're looking for in a candidate using natural language

5. Click "Find Matching Candidates" to process the resumes

6. View your results and export them to Excel if needed

## How It Works

1. **Upload**: Multiple resume files (PDF, DOCX, TXT) are processed in batches
2. **Natural Language Processing**: Your requirements are converted into structured criteria
3. **AI Analysis**: Each resume is analyzed by Azure OpenAI GPT-4o
4. **Smart Matching**: Candidates are ranked with detailed match explanations
5. **Custom Information**: Extract any specific information you need with a simple prompt

## Coming Soon

- Email fetching to automatically process resumes from your inbox
- More visualization options for candidate comparison
- Advanced filtering capabilities

## License

This project is licensed under the MIT License - see the LICENSE file for details.
