import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

# Server configuration
HOST = os.getenv('HOST', '127.0.0.1')
PORT = int(os.getenv('PORT', 8000))

# OpenAI configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY must be set in .env file")
SERPER_API_KEY = os.getenv('SERPER_API_KEY')
if not SERPER_API_KEY:

# Configure default language model
default_langchain_model = ChatOpenAI(
    model="gpt-4-turbo-preview",
    temperature=0
)

# Logging configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')