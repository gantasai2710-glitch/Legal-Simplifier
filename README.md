<div align="center">
  <h1>⚖️ Legal Text Simplifier</h1>
  <p><strong>Decode complex legal language into plain English with AI.</strong></p>
</div>

An AI-powered application designed to break down dense legal documents (NDAs, terms of service, contracts) into easily accessible, plain-English components. By acting as both an expert translator and a legal risk analyst, it empowers users to understand exactly what they are signing without needing expensive legal counsel.

## ✨ Features

* **📝 Plain-English Translation:** Translates highly technical "legalese" into a clear, 8th-grade reading level format using clean Markdown bullet points.
* **🚨 Anomaly & Risk Detection:** Automatically scans the document to flag hidden financial traps, highly one-sided clauses, and unusual obligations.
* **📖 Dynamic Glossary Generation:** Isolates archaic legal jargon (e.g., *indemnify*, *hereinafter*) and provides simple, contextual definitions.
* **🏗️ Structured Data Extraction:** Built on strict JSON schemas to deterministically extract all insights (Summary, Translation, Risks, Glossary) simultaneously in a single, hyper-efficient API call.
* **📄 PDF Support:** Directly upload complex PDF contracts for instant optical text extraction and analysis.

## 🛠️ Technology Stack

* **Frontend & Backend:** [Streamlit](https://streamlit.io/) (Unified Python web framework)
* **AI & LLM:** Google Gemini 2.5 Flash API
* **Data Validation:** Pydantic
* **Document Parsing:** PyMuPDF (`fitz`)
* **Environment Management:** `python-dotenv`

## 🚀 Setup & Installation Instructions

Follow these steps to run the Legal Text Simplifier locally on your machine.

### 1. Prerequisites
Ensure you have Python 3.10 or higher installed. You will also need a free API key from Google AI Studio.
* Get your API key here: [Google AI Studio](https://aistudio.google.com/app/apikey)

### 2. Clone the Repository
Open your terminal and run:
```bash
git clone https://github.com/yourusername/legal-simplifier.git
cd legal-simplifier
```

### 3. Create a Virtual Environment (Recommended)
Isolate your project dependencies:
```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies
Install all required packages from the `requirements.txt` file:
```bash
pip install -r requirements.txt
```

### 5. 🔑 CRITICAL: Set Up Environment Variables
For security, API keys are never hardcoded into this repository. You must create your own environment file.
1. Create a new file in the root directory and name it exactly `.env`.
2. Open `.env` in your text editor and add your Gemini API key like this:
```env
GEMINI_API_KEY="your_actual_api_key_here"
```
*(Note: The `.env` file is explicitly listed in our `.gitignore`, ensuring your private key will never be accidentally leaked or committed to GitHub).*

### 6. Run the Application
Start the Streamlit server:
```bash
streamlit run app.py
```
The application will automatically launch in your default web browser at `http://localhost:8501`.

---

> **Disclaimer:** This tool is for educational and informational purposes only. It does not constitute formal legal advice. Always consult with a qualified 


attorney for binding legal decisions.
******************************************************
