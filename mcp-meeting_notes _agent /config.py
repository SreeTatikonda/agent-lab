import os
from dotenv import load_dotenv

# Load local environment variables from .env file
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# Determine if we should run in Mock Mode (offline simulation)
MOCK_MODE = not GEMINI_API_KEY or GEMINI_API_KEY.strip() == "" or GEMINI_API_KEY == "your_gemini_api_key_here"

def get_genai_client():
    """
    Initializes and returns the modern GenAI Client.
    Returns None if in MOCK_MODE.
    """
    if MOCK_MODE:
        return None
    try:
        from google import genai
        return genai.Client(api_key=GEMINI_API_KEY)
    except ImportError:
        # Gracefully handle import error if package is not installed yet
        raise ImportError(
            "Could not import 'google-genai' library. Make sure to run 'pip install -r requirements.txt'"
        )
