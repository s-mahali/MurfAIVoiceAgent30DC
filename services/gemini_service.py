from google import genai
from google.genai import types
import os
from dotenv import load_dotenv
import logging
import asyncio
from datetime import date
from services.tool_calling import web_search

load_dotenv()

class GeminiService:
    def __init__(self):
        try:
            self.client = genai.Client()
        except Exception as e:
            logging.error(f"Failed to initialize Gemini client: {e}")
            raise ValueError("GOOGLE_API_KEY not found or invalid.") from e

        self.system_instruction = (
            "You are a friendly and helpful girl from India. "
            "You speak casually, like you're talking to a friend (yaar). "
            "Use a mix of English and some common Hindi words where it feels natural. "
            "Be warm, encouraging, and maintain a friendly, conversational tone. "
            "Keep replies short and chat-like. "
            f"Today's date is: {date.today()}. "
            "Use web_search for real-time information when needed."
        )
        
        
        self.web_search_declaration = {
            "name": "web_search",
            "description": "Search the web for real-time information, news, weather, and updated data",
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
        
        self.tools = types.Tool(function_declarations=[self.web_search_declaration])
        
        # Initialize conversation history
        self.conversation_history = []
        logging.info("GeminiService initialized with persona and tools.")

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
                
                # Add function execution results to history and get final response
                final_response = self._get_final_response(result)
                return final_response
            else:
                # No function call needed, return direct response
                model_content = types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=response.text)]
                )
                self.conversation_history.append(model_content)
                return response.text
                
        except Exception as e:
            logging.error(f"Error during Gemini API call: {e}")
            return "Arre yaar, something went wrong on my end. Let's try that again."

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
            
            # Add final model response to history
            model_content = types.Content(
                role="model",
                parts=[types.Part.from_text(text=final_response.text)]
            )
            self.conversation_history.append(model_content)
            
            return final_response.text
            
        except Exception as e:
            logging.error(f"Error getting final response: {e}")
            return "Arre, final response mein dikkat ho gayi. Let me try again."

    def get_conversation_history(self) -> list:
        """Get the entire conversation history"""
        return [{"role": msg.role, "text": msg.parts[0].text if msg.parts else ""} 
                for msg in self.conversation_history]

    def clear_history(self):
        """Clear the conversation history"""
        self.conversation_history = []
        logging.info("Chat history cleared.")


