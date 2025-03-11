# AI-Powered Resume Parser with Azure OpenAI Integration

A Streamlit application for parsing, filtering, and analyzing multiple resumes based on custom criteria, powered by Azure OpenAI GPT-4o for high-accuracy information extraction.

## Features

- **Advanced Azure OpenAI GPT-4o Integration**: Leverages GPT-4o's capabilities with smart rate limiting and queue-based processing for reliable resume analysis
- **Interactive Matching System**: Shows match scores and specific reasons why candidates match your criteria
- **Structured Data Extraction**: Extract detailed work history, education, skills, and more in a structured format
- **Advanced Custom Fields**: Define and extract custom data points from resumes using natural language prompts
- **Bulk File Handling**: Process multiple resume files (PDF, DOCX, TXT) at once
- **Customizable Columns**: Choose which resume details to display
- **Advanced Filtering**: Filter candidates by skills, experience, education level, and more
- **Data Visualization**: View skill distribution and compare candidate qualifications
- **Excel Export**: Download filtered results as an Excel spreadsheet

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Azure OpenAI API key with GPT-4o access

### Setup

1. Clone the repository or download the source code:

```bash
git clone <repository-url>
cd resume-parser
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

## Azure OpenAI Setup

1. Create an Azure OpenAI resource:
   - Go to the [Azure Portal](https://portal.azure.com/)
   - Search for "OpenAI" and create a new resource
   - Once deployed, deploy a model (GPT-4o)
   - Get your API key from the resource's "Keys and Endpoint" section
   - Configure the endpoint URL in the secrets file

2. This application requires Azure OpenAI to function correctly. Make sure your API key and endpoint are properly configured.

## Usage

1. Start the Streamlit application:

```bash
streamlit run app.py
```

2. Access the application in your web browser (typically at http://localhost:8501)

3. Ensure your Azure OpenAI credentials are configured properly

4. Upload resume files using the file uploader in the sidebar

5. Click "Process Resumes" to extract information from the uploaded files

6. Define your filtering criteria and click "Apply Filters" - the system will use your criteria to enhance the analysis

7. View the filtered results, match scores, and detailed analysis

8. Export to Excel or CSV if needed

## Advanced Features

### Smart Rate Limiting

The application incorporates an intelligent rate limiting system to handle Azure OpenAI API quotas:

1. Adaptive backoff that responds to API rate limits automatically
2. Queue-based processing with batched file handling
3. Detailed status tracking for each document
4. Exponential retry logic with jitter for optimal throughput

### Context-Aware Analysis

The application uses a two-pass system for resume analysis:

1. Initial parsing extracts basic information from resumes
2. When filter criteria are applied, the system reanalyzes the resumes with your specific criteria to provide more relevant matching and scoring

### Match Scoring

The system calculates a match score (0-100%) for each candidate based on how well they match your filter criteria. It also provides detailed explanations for why candidates are considered good matches.

### Custom Fields

You can define custom fields to extract from resumes using natural language prompts. For example:
- "Extract years of Python experience"
- "Identify whether the candidate has worked in healthcare"
- "Determine if the candidate has leadership experience"

## Project Structure

```
resume_parser/
│
├── app.py                    # Main Streamlit application
├── requirements.txt          # Project dependencies
├── README.md                 # Project documentation
│
├── .streamlit/
│   └── secrets.toml          # Azure API credentials (not in version control)
│
├── utils/
│   ├── __init__.py
│   ├── file_handler.py       # File upload and handling functions
│   ├── filters.py            # Resume filtering functions
│   ├── export.py             # Excel export functionality
│   ├── azure_openai.py       # Azure OpenAI GPT-4o integration
│   └── secrets_manager.py    # Secrets management utility
│
└── data/
    ├── uploads/              # Temporary storage for uploaded files
    └── processed/            # Storage for processed resume data
```

## Security Notes

- Your Azure API credentials should never be committed to version control
- The `.streamlit/secrets.toml` file is included in `.gitignore` by default
- For production deployment, use Streamlit's secrets management or environment variables

## License

This project is licensed under the MIT License - see the LICENSE file for details.
