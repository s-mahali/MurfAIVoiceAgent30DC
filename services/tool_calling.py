from tavily import TavilyClient
import os
from dotenv import load_dotenv
import asyncio
import logging
from config.config import api_keys
load_dotenv()

tavily = TavilyClient(api_key=api_keys.tavily)

async def web_search(query: str) -> dict:
   
    try:
        # Ensure query is a string, not dict
        if isinstance(query, dict):
            query = query.get("query", "")
        
        print(f"Calling web search tool with query: {query}")
        response = await asyncio.to_thread(tavily.search, query)
        
        # Validate response structure
        if not isinstance(response, dict):
            return {"status": "error", "message": "Invalid response type from Tavily"}
        
        results = response.get("results", [])
        final_result = "\n\n".join([result.get('content', '') for result in results[:3]])
        
        print("Search successful, results length:", len(final_result))
        return {"status": "success", "results": final_result}
        
    except Exception as e:
        logging.error(f"Error during web search: {e}")
        return {"status": "error", "message": str(e)}
        
        


