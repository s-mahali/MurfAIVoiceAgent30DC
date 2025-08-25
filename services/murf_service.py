import os
from murf import Murf
from dotenv import load_dotenv
import asyncio
import websockets
import json
import base64
import logging
from typing import Optional

load_dotenv()
MURF_API_KEY = os.getenv('MURF_API_KEY')


# non-streaming murf service 
async def murf_tts(text: str) -> dict:
    """
    Generate an audio file from the given text using Murf's text-to-speech API.

    Args:
        text (str): The text to convert to audio.

    Returns:
        dict: A dictionary containing the generated audio file, or an error message if the text is empty or no audio file is generated.
    """
    client = Murf(
        api_key=MURF_API_KEY
    )

    if not text or not text.strip():
        return {"error": "Missing text"}
    res = client.text_to_speech.generate(
        text=text,
        voice_id="en-US-Ken"
    )

    if not res.audio_file:
        return {"error": "No audio file generated"}

    return {"audio_file": res.audio_file}

WS_URL = "wss://api.murf.ai/v1/speech/stream-input"

class MurfService:
    def __init__(self, websocket, api_key: str):
        self.websocket = websocket
        self.api_key = api_key
        self.ws_url = WS_URL
        self.connection: Optional[websockets.WebSocketClientProtocol] = None
        
    async def connect(self):
        """Connect to the Murf WebSocket API."""
        try:
            self.connection = await websockets.connect(
                f"{self.ws_url}?api_key={self.api_key}&sample_rate=44100&channel_type=MONO&format=WAV"
            )
            print("Connected to Murf.ai TTS service")
            
            #send voice configuration
            voice_config = {
                "voice_config": {
                    "voiceId": "en-US-amara",  
                    "style": "Conversational",
                    "rate": 0,
                    "pitch": 0,
                    "variation": 1
                }
            }
            await self.connection.send(json.dumps(voice_config))
        
        except Exception as e:
            logging.error(f"Failed to connect to Murf.ai: {e}")
            raise
        
    async def synthesize_speech(self, text:str):
        """Convert text to speech and return base64 audio"""
        if not self.connection:
            await self.connect()    
            
        try:
            #send text to be synthesized
            text_message = {
                'text': text,
                'end': True,
                 
                
            }
            await self.connection.send(json.dumps(text_message))
            asyncio.create_task(self._receive_audio_stream())
        
        except Exception as e:
            logging.error(f"Failed to synthesize speech: {e}")
            raise
        
    async def _receive_audio_stream(self):
        """Handle audio streaming in background"""
        try:
           while True:
              response = await self.connection.recv()
              data = json.loads(response)
            
              if "audio" in data:
                await self.websocket.send_json({
                    "status": "audio_chunk",
                    "audio_base64": data["audio"],
                    "is_complete": False
                })
            
              if data.get("final"):
                await self.websocket.send_json({
                    "status": "audio_complete"
                })
                await self.websocket.send_json({
                    "status": "bot_speaking",
                    "active": False
                })
                break
                
        except Exception as e:
          logging.error(f"Audio streaming error: {e}")        
        
    async def close(self):
        """Close the WebSocket connection"""
        if self.connection:
            await self.connection.close()
            self.connection = None
            print("Murf.ai connection closed")        