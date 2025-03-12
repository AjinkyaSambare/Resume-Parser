# ResumeParser

A modern, AI-powered resume parsing application with natural language filtering capabilities.

## Features

- **Clean, Modern UI**: Intuitive interface for uploading and analyzing resumes
- **Natural Language Filtering**: Use everyday language to find the perfect candidates
- **Multiple File Formats**: Support for PDF, DOC, DOCX, and TXT resume formats
- **Custom Columns**: Extract specific information from resumes with a simple prompt
- **Export Functionality**: Easily export your parsed data to Excel
- **Sample Data**: Try the app with sample resumes to see how it works

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Google Gemini API key (optional but recommended for advanced features)

### Setup

1. Clone the repository:

```bash
git clone <repository-url>
cd ResumeParser
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

4. Configure Google Gemini (optional):

Create a `.streamlit/secrets.toml` file with your Gemini API key:

```toml
# Google Gemini API credentials
[gemini]
api_key = "your_gemini_api_key_here"
```

## Usage

1. Start the Streamlit application:

```bash
streamlit run app.py
```

2. Access the application in your web browser (typically at http://localhost:8501)

3. Upload resume files by dragging and dropping or browsing your computer

4. Use natural language to filter candidates (e.g., "Java developers with 5+ years experience")

5. View the results and export them to Excel if needed

## How It Works

1. **Upload**: Drag and drop your resume files (PDF, DOC, DOCX, TXT)
2. **Process**: AI-powered parsing extracts structured information from each resume
3. **Filter**: Use natural language to find candidates matching your criteria
4. **Customize**: Add custom columns to extract specific information from resumes
5. **Export**: Download the results as an Excel file for further analysis

## Sample Data

The application comes with a sample data option. Click "Load sample resumes" to try the application with pre-loaded sample resumes.

To add your own sample data:
1. Create PDF or DOCX resume files
2. Place them in the `data/samples` directory
3. They will be available when you click the "Load sample resumes" button

## License

This project is licensed under the MIT License - see the LICENSE file for details.
