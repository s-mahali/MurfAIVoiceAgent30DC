import os
from dotenv import load_dotenv

load_dotenv()

class ApiKeys:
    def __init__(self):
        self.murf = os.getenv("MURF_API_KEY", "")
        self.assemblyai = os.getenv("ASSEMBLYAI_API_KEY", "")
        self.gemini = os.getenv("GEMINI_API_KEY", "")
        self.tavily = os.getenv("TAVILY_API_KEY", "")
    
    def update_keys(self, new_keys):
        if "murf" in new_keys and new_keys["murf"]:
            self.murf = new_keys["murf"]
        if "assemblyai" in new_keys and new_keys["assemblyai"]:
            self.assemblyai = new_keys["assemblyai"]
        if "gemini" in new_keys and new_keys["gemini"]:
            self.gemini = new_keys["gemini"]
        if "tavily" in new_keys and new_keys["tavily"]:
            self.tavily = new_keys["tavily"]

#singleton instance
api_keys = ApiKeys()