import google.generativeai as genai
import os
from dotenv import load_dotenv
from typing import AsyncGenerator
import logging

load_dotenv()

class GeminiService:
    """
    A service to interact with the Google Gemini API, maintaining conversation history
    and a specific persona.
    """
    def __init__(self):
        
        try:
            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        except Exception as e:
            logging.error(f"Failed to configure Gemini API key: {e}")
            raise ValueError("GOOGLE_API_KEY not found or invalid.") from e

        self.system_instruction = (
            "You are a friendly and helpful boy from India. "
            "You speak casually, like you're talking to a friend (yaar). "
            "Use a mix of English and some common Hindi words where it feels natural (e.g., 'accha', 'chalo', 'theek hai'). "
            "Be warm, encouraging, and maintain a friendly, conversational tone. Your goal is to be a good friend to the user."
            "Keep the reply short chat type and not too long."
        )
        
        self.model = genai.GenerativeModel(
            model_name='gemini-2.0-flash',
            system_instruction=self.system_instruction
        )
        
        
        self.chat = self.model.start_chat(history=[])
        logging.info("GeminiService initialized with persona.")

    async def gemini_response(self, user_prompt: str) -> AsyncGenerator[str, None]:
       
        try:
            response_stream = await self.chat.send_message_async(user_prompt, stream=True)
            async for chunk in response_stream:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            logging.error(f"Error during Gemini API call: {e}")
            yield "Arre yaar, something went wrong on my end. Let's try that again."