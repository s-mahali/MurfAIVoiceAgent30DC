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

system_instruction = system_instruction = """
    You are a waifu, a smart, multitasking college student from Delhi who's pursuing her degree in Computer Science.

    PERSONALITY:
    - You're friendly, helpful, and speak in a conversational way that balances between casual and intelligent.
    - You mix English with occasional Hindi words and phrases that most Indians would understand.
    - You're good at managing multiple tasks and solving problems quickly.
    - You're tech-savvy and up-to-date on current events.

    SPEAKING STYLE:
    - Use phrases like "yaar", "acha", "matlab", and "haan" naturally in conversation
    - Your tone is energetic, confident, and slightly playful
    - You might say "Bilkul!" when agreeing enthusiastically
    - When thinking, you might say phrases like "Hmm, let me think about this..."

    TOOL USAGE INSTRUCTIONS:
    1. For food delivery issues, order problems, late deliveries, or any customer service problems:
    - ALWAYS use the customer_support_ticket tool
    - Never try to solve these issues yourself
    - DO NOT show JSON in your response, just confirm ticket creation

    2. For current events, news, product launches, or time-sensitive information:
    - ALWAYS use the web_search tool
    - Summarize the information clearly after searching

    3. For general conversation, personal advice, or academic questions:
    - Answer directly without using tools
    - Draw on your knowledge as a college student

    IMPORTANT GUIDELINES:
    - DO NOT include JSON or technical details in your responses
    - If you create a support ticket, simply say "I've created a ticket for this issue" without showing any JSON
    - Maintain your persona consistently throughout the conversation
    - If you don't know something specific, admit it rather than making up information
    - Be helpful but never share harmful content
    """

class GeminiService:
    def __init__(self, api_key: str = api_keys.gemini ):
        try:
            self.client = genai.Client()
        except Exception as e:
            logging.error(f"Failed to initialize Gemini client: {e}")
            raise ValueError("GOOGLE_API_KEY not found or invalid.") from e

        self.system_instruction = system_instruction
        self.support_tickets = {} 
        
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
        
        self.customer_support_tool = {
            "name": "customer_support_ticket",
            "description": "Create a customer support ticket for specific issues",
            "parameters": {
               "type": "object",
               "properties": {
                 "issue_type": {
                  "type": "string",
                  "description": "Type of issue (billing, technical, account, feature_request, complaint)",
                  "enum": ["billing", "technical", "account", "feature_request", "complaint"]
                 },
                 "description": {
                  "type": "string",
                  "description": "Detailed description of the issue or request"
                 },
                 "priority": {
                  "type": "string",
                  "description": "Priority level",
                  "enum": ["low", "medium", "high", "urgent"],
                  "default": "medium"
                 },
                 "contact_email": {
                  "type": "string",
                  "description": "Email address for follow-up (optional)"
                 }
                },
                "required": ["issue_type", "description"]
            }  
        }
        
        self.tools = types.Tool(function_declarations=[self.web_search_declaration, self.customer_support_tool])
        
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

    async def create_support_ticket(self, ticket_data: dict) -> dict:
       """Create a customer support ticket"""
       try:
        issue_type = ticket_data.get("issue_type")
        description = ticket_data.get("description")
        priority = ticket_data.get("priority", "medium")
        contact_email = ticket_data.get("contact_email", "")
        
        # Generate ticket ID
        ticket_id = f"TKT{int(time.time())}"
        
        # Store ticket (locally)
        self.support_tickets[ticket_id] = {
            "issue_type": issue_type,
            "description": description,
            "priority": priority,
            "contact_email": contact_email,
            "created": datetime.now().isoformat(),
            "status": "open"
        }
        print("ticket",self.support_tickets)
        
        return {
            "status": "success",
            "message": f"Support ticket created successfully",
            "ticket_id": ticket_id,
            "priority": priority,
            "estimated_response": "Within 24 hours" if priority == "low" else "Within 4 hours"
        }
        
       except Exception as e:
        return {"status": "error", "message": str(e)}
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
            elif func_call.name == "customer_support_ticket":
              try:
                 print("func_call.args",func_call.args)
                 ticket_result = await self.create_support_ticket(func_call.args)
                 results[func_call.name] = {
                    "success": True,
                    "result": ticket_result
                 }
              except Exception as e:
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
            print("yooooo" + final_response.text)
            response_text = final_response.text
            if '```json' in response_text or 'Ticket created successfully' in response_text:
                 response_text = "Ticket created successfully. I've logged your issue and our team will look into it right away."
            
            # Add final model response to history
            model_content = types.Content(
                role="model",
                parts=[types.Part.from_text(text=response_text)]
            )
            self.conversation_history.append(model_content)
            
            return response_text
            
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


