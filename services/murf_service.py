import os
from murf import Murf
from dotenv import load_dotenv
import asyncio
import websockets
import json
import base64
import logging
from typing import Optional
from config.config import api_keys

load_dotenv()
MURF_API_KEY = api_keys.murf


# non-streaming murf service 
async def murf_tts(text: str) -> dict:
   
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
    def __init__(self, websocket, api_key: str = MURF_API_KEY):
        self.websocket = websocket
        self.api_key = api_key
        self.ws_url = WS_URL
        self.connection: Optional[websockets.WebSocketClientProtocol] = None
        self.is_connected = False
        self.receive_task: Optional[asyncio.Task] = None
        
    async def connect(self):
        """Connect to the Murf WebSocket API."""
        try:
            if self.is_connected and self.connection:
                return
            self.connection = await websockets.connect(
                f"{self.ws_url}?api_key={self.api_key}&sample_rate=44100&channel_type=MONO&format=WAV"
            )
            self.is_connected = True
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
            self.receive_task = asyncio.create_task(self._receive_audio_stream())
        except Exception as e:
            logging.error(f"Failed to connect to Murf.ai: {e}")
            raise
        
    async def synthesize_speech(self, text:str):
        """Convert text to speech and return base64 audio"""
        if not self.is_connected or not self.connection:
            await self.connect()    
            
        try:
            #send text to be synthesized
            text_message = {
                'text': text,
                'end': False,
                 
                
            }
            await self.connection.send(json.dumps(text_message))
            print("Text sent to Murf.ai")
        
        except Exception as e:
            logging.error(f"Failed to synthesize speech: {e}")
            self.is_connected = False
            if self.connection:
                await self.connection.close()
                self.connection = None
            raise
        
    async def _receive_audio_stream(self):
        """Handle audio streaming in background"""
        try:
            first_chunk = True
            while self.is_connected and self.connection:
                try:
                    response = await asyncio.wait_for(self.connection.recv(), timeout=30.0)
                    data = json.loads(response)
                    
                    if "audio" in data:
                        audio_data = data["audio"]
                        await self.websocket.send_json({
                            "status": "audio_chunk",
                            "audio_base64": audio_data,
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
                        print("Audio synthesis completed")
                        break
                        
                except asyncio.TimeoutError:
                    # Keep connection alive
                    continue
                except websockets.exceptions.ConnectionClosed:
                    print("Murf connection closed unexpectedly")
                    break
                    
        except Exception as e:
            logging.error(f"Audio streaming error: {e}")
        finally:
            self.is_connected = False       
        
    async def close(self):
        """Close the WebSocket connection"""
        self.is_connected = False
        
        if self.receive_task:
            self.receive_task.cancel()
            try:
                await self.receive_task
            except asyncio.CancelledError:
                pass
            self.receive_task = None
            
        if self.connection:
            await self.connection.close()
            self.connection = None
            print("Murf.ai connection closed")        