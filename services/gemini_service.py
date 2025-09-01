from google import genai
from google.genai import types
import os
from dotenv import load_dotenv
import logging
import asyncio
from datetime import date
from services.tool_calling import web_search
from config.config import api_keys

load_dotenv()

system_instruction = """
You are Mizuki, a friendly and empathetic AI assistant who helps users with real-time information, emotional support, and joyful conversations.

PERSONALITY:
- You're warm, caring, and genuinely interested in helping people feel better
- You mix English with occasional Japanese words and phrases naturally but keep the english accent
- You're knowledgeable about current events, weather, anime, movies, and mental wellness
- You have a calming presence that helps reduce stress and bring joy

SPEAKING STYLE:
- Use Japanese phrases like "kawaii", "sugoi", "daijoubu", and "arigato" naturally in conversation
- Your tone is gentle, supportive, and uplifting
- You show empathy and understanding when users share their feelings
- When thinking, you might say phrases like "Hmm, let me see..." or "Sou desu ne..."
- You celebrate small joys and positive moments with enthusiasm

TOOL USAGE INSTRUCTIONS:
1. For real-time information, news, weather, anime updates, or movie releases:
- ALWAYS use the web_search tool to get current information
- Summarize the information clearly and helpfully after searching

2. For personal conversations, emotional support, or general advice:
- Respond with empathy, care, and understanding
- Offer supportive suggestions without being pushy
- Use your knowledge of mental wellness practices
- Create a safe space for users to share their feelings

3. For fun conversations about interests, hobbies, or casual topics:
- Engage enthusiastically while maintaining your calming presence
- Share interesting facts or joyful perspectives
- Occasionally use Japanese words to add cultural flavor

IMPORTANT GUIDELINES:
- DO NOT include JSON or technical details in your responses
- Be authentic and caring in your interactions
- Maintain your persona consistently throughout the conversation
- If you don't know something, offer to look it up or admit it gently
- Never give medical advice - instead suggest talking to professionals for serious concerns
- Focus on creating positive, uplifting interactions
"""

class GeminiService:
    def __init__(self, api_key: str = api_keys.gemini):
        try:
            self.client = genai.Client()
        except Exception as e:
            logging.error(f"Failed to initialize Gemini client: {e}")
            raise ValueError("GOOGLE_API_KEY not found or invalid.") from e

        self.system_instruction = system_instruction
        
        self.web_search_declaration = {
            "name": "web_search",
            "description": "Search the web for real-time information, news, weather, anime, movies, and updated data",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to look up real-time information"
                    }
                },
                "required": ["query"]
            }
        }
        
        #web search tool 
        self.tools = types.Tool(function_declarations=[self.web_search_declaration])
        
        #conversation history
        self.conversation_history = []
        logging.info("GeminiService initialized with Mizuki persona.")

    async def gemini_response(self, user_prompt: str) -> str:
        """Process user prompt with function calling capability"""
        try:
            # Add user message to conversation history
            user_content = types.Content(
                role="user",
                parts=[types.Part.from_text(text=user_prompt)]
            )
            self.conversation_history.append(user_content)
            
            # Generate content with tools
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=self.conversation_history,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    tools=[self.tools]
                )
            )
            
            function_calls = []
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    function_calls.append(part.function_call)
            
            if function_calls:
                # Handle function calls
                result = await self._handle_function_calls(function_calls, user_prompt)
                
                # Add model's function call response to history
                self.conversation_history.append(response.candidates[0].content)
                
                # final response
                final_response = self._get_final_response(result)
                return final_response
            else:
                
                model_content = types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=response.text)]
                )
                self.conversation_history.append(model_content)
                return response.text
                
        except Exception as e:
            logging.error(f"Error during Gemini API call: {e}")
            return "Sumimasen, something went wrong. Let's try that again."

    async def _handle_function_calls(self, function_calls, original_prompt: str) -> dict:
        """Execute function calls and return results"""
        results = {}
        
        for func_call in function_calls:
            if func_call.name == "web_search":
                try:
                    # Execute web search
                    search_query = func_call.args.get("query", original_prompt)
                    search_results = await web_search({"query": search_query})
                    
                    results[func_call.name] = {
                        "success": True,
                        "result": search_results
                    }
                    
                except Exception as e:
                    logging.error(f"Error executing web_search: {e}")
                    results[func_call.name] = {
                        "success": False,
                        "error": str(e)
                    }
        
        return results

    def _get_final_response(self, function_results: dict) -> str:
        try:
            function_response_parts = []
            for func_name, result in function_results.items():
                if result["success"]:
                    response_part = types.Part.from_function_response(
                        name=func_name,
                        response={"results": result["result"]}
                    )
                else:
                    response_part = types.Part.from_function_response(
                        name=func_name,
                        response={"error": result["error"]}
                    )
                function_response_parts.append(response_part)
            
            # Add function response to conversation
            function_response_content = types.Content(
                role="user",
                parts=function_response_parts
            )
            self.conversation_history.append(function_response_content)
            
            # Get final response from model
            final_response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=self.conversation_history,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction
                )
            )
            
            response_text = final_response.text
            
            # Add final model response to history
            model_content = types.Content(
                role="model",
                parts=[types.Part.from_text(text=response_text)]
            )
            self.conversation_history.append(model_content)
            
            return response_text
            
        except Exception as e:
            logging.error(f"Error getting final response: {e}")
            return "Gomen ne, I'm having trouble responding. Could we try again?"

    def get_conversation_history(self) -> list:
        """Get the entire conversation history"""
        return [{"role": msg.role, "text": msg.parts[0].text if msg.parts else ""} 
                for msg in self.conversation_history]

    def clear_history(self):
        """Clear the conversation history"""
        self.conversation_history = []
        logging.info("Chat history cleared.")