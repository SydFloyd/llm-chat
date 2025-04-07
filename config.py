from dotenv import load_dotenv
import os

load_dotenv()

class Config:
    def __init__(self):
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")

cfg = Config()