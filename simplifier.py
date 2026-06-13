import os
import json
from google import genai
from google.genai import types
from google.genai import errors
from pydantic import BaseModel, Field

class GlossaryItem(BaseModel):
    term: str = Field(description="Archaic legalese word found (e.g., indemnity, hereinafter)")
    definition: str = Field(description="Simple plain-English definition")

class SimplifiedLegalText(BaseModel):
    summary: str = Field(description="A concise 2-3 sentence plain-English overview of the clause's core purpose.")
    simplified_text: str = Field(description="The plain-English translation (8th-grade reading level) formatted with clean Markdown bullet points.")
    key_risks: list[str] = Field(description="An array of hidden traps, highly one-sided clauses, severe penalties, or unusual obligations found in the text.")
    glossary: list[GlossaryItem] = Field(description="Glossary of archaic legalese words found and their definitions.")

def simplify_text(text: str) -> dict:
    """Simplify legal language using Gemini API with Structured Output."""
    if not os.path.exists(".env"):
        return {
            "error": "Missing Configuration File",
            "message": "The .env file is missing from the root directory. Please create a .env file and add your GEMINI_API_KEY."
        }
        
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        return {
            "error": "Missing API Key",
            "message": "GEMINI_API_KEY is not set in your environment. Please add it to your .env file."
        }
    
    client = genai.Client(api_key=api_key)
    
    prompt = f"Here is the legal text to analyze and simplify:\n\n{text}"
    
    sys_instruction = (
        "You are an expert legal translator and risk analyst. Your job is to take complex "
        "legal text, translate it into simple, 8th-grade level plain English, and identify risks. "
        "CRITICAL CONSTRAINT: You must NEVER mutate, hallucinate, or alter the identity of the parties involved. "
        "They must remain strictly mapped as 'Party 1', 'Party 2', or their explicit defined names. "
        "Strip away all legalese but maintain exact party names. Use bullet points for the simplified text. "
        "Flag clauses that heavily favor one party or introduce hidden financial liabilities in key_risks."
    )
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=sys_instruction,
                max_output_tokens=8192,
                temperature=0.3,
                response_mime_type="application/json",
                response_schema=SimplifiedLegalText,
            ),
        )
        
        try:
            result = json.loads(response.text)
            return result
        except json.JSONDecodeError as e:
            return {
                "error": "Truncated Output",
                "message": f"The AI response was cut off or returned invalid JSON. The document might be too long. Error details: {str(e)}"
            }
        
    except errors.APIError as e:
        status_code = getattr(e, 'code', None)
        if status_code == 401:
            return {
                "error": "Unauthorized",
                "message": "Your Gemini API Key is invalid or expired. Please check your .env file."
            }
        elif status_code == 429:
            return {
                "error": "Rate Limit Exceeded",
                "message": "Too many requests. Please wait a moment and try again."
            }
        else:
            return {
                "error": "API Error",
                "message": f"An error occurred with the Gemini API: {str(e)}"
            }
    except Exception as e:
        return {
            "error": "Processing Error",
            "message": f"A network or processing error occurred: {str(e)}"
        }
