from fastapi import UploadFile
import assemblyai as aai
from dotenv import load_dotenv
import os
import asyncio
import logging
from typing import Type
from google import genai
import time
from datetime import datetime, timedelta
from collections import deque
from services.murf_service import MurfService
from services.gemini_service import GeminiService
from assemblyai.streaming.v3 import (
    BeginEvent,
    StreamingClient,
    StreamingClientOptions,
    StreamingError,
    StreamingEvents,
    StreamingParameters,
    StreamingSessionParameters,
    TerminationEvent,
    TurnEvent,
)

load_dotenv()
aai.settings.api_key =  os.getenv('ASSEMBLYAI_API_KEY')

class AssemblyAIStreamingClient:
    def __init__(self, websocket, loop, sample_rate=16000, silence_threshold=0.6):
        self.websocket = websocket
        self.loop = loop
        self.silence_threshold = silence_threshold #second of silence to trigger LLM
        self.last_audio_time = None
        self.transcript = ""
        self.llm_task = None
        self.is_processing = False
        
        
        #Initialize MurfService
        self.murf_service = MurfService(
            websocket = websocket,
            api_key=os.getenv("MURF_API_KEY")
        )
        
        #Initialize GeminiService
        self.gemini_service = GeminiService()
        
          # Initialize AssemblyAI client
        self.client = StreamingClient(
            StreamingClientOptions(
                api_key= aai.settings.api_key,
                api_host= "streaming.assemblyai.com"
                
            )
        )
        # Set up event handlers
        self.client.on(StreamingEvents.Begin, self.on_begin)
        self.client.on(StreamingEvents.Turn, self.on_turn)
        self.client.on(StreamingEvents.Termination, self.on_terminated)
        self.client.on(StreamingEvents.Error, self.on_error)
        
        # Connect with parameters
        self.client.connect(StreamingParameters(
            sample_rate=sample_rate, format_turns=False
        ))
    
    def on_begin(self, client, event: BeginEvent):
       print(f"Session started: {event.id}")
       self.last_audio_time = time.time()
    
    def on_turn(self, client, event: TurnEvent):
        current_time = time.time()
        #update last audio time 
        self.last_audio_time = current_time
        print(f"transcript: {event.transcript}, end_of_turn: {event.end_of_turn}")
        self.transcript = event.transcript 
           
       
        if event.end_of_turn and event.transcript:
            print("calling process_buffered_transcript")
            asyncio.run_coroutine_threadsafe(
            self.process_buffered_transcript(),
            self.loop
        )
        else:
            print("calling check_silence_and_process")
            asyncio.run_coroutine_threadsafe(
            self.check_silence_and_process(),
            self.loop
        )
      
      
        if event.end_of_turn and not event.turn_is_formatted:
          client.set_params(StreamingSessionParameters(format_turns=True))
    
    
    async def check_silence_and_process(self):
        print("Checking silence...")
        """Check if enough silence has passed and process transcript"""
        if (self.last_audio_time and time.time() - self.last_audio_time > self.silence_threshold
            and self.transcript and  not self.is_processing):
            print("Enough silence has passed, processing transcript...")
            await self.process_buffered_transcript()
        else:
            print("Not enough silence, skipping processing...")
    async def process_buffered_transcript(self):
        print("1Processing buffered transcript...")
        if not self.transcript or self.is_processing:
            print("No transcript or is_processing, skipping processing...")
            return
        
        self.is_processing = True
        
        await self.websocket.send_json({
               "status": "transcript",
               "text": self.transcript,
               })
        print("Sent transcript to client", self.transcript)
        
        final_transcript = self.transcript
        self.transcript = ""
        
        # Call LLM asynchronously
        self.llm_task = asyncio.run_coroutine_threadsafe(
            self.call_llm_async(final_transcript),
            self.loop,
            
        )
        print("LLM task started")
    
    async def call_llm_async(self, text: str):
        print("Calling LLM...")
        try:
            
            llm_response = await self.gemini_service.gemini_response(text)
                 
            
            # Send completion signal
            await self.websocket.send_json({
                "status": "llm_response",
                "text": llm_response,
                "is_complete": True
            })
            
            # Notify client that bot is about to speak (pause mic streaming)
            await self.websocket.send_json({
                "status": "bot_speaking",
                "active": True
            })
            #Convert LLM response to speech using Murf.ai
            if llm_response.strip():
                print("Converting LLM response to speech...")
                await self.murf_service.synthesize_speech(llm_response)
                
            
        except Exception as e:
            logging.error(f"LLM Error: {e}")
            await self.websocket.send_json({
                "status": "error",
                "message": str(e)
            })
        finally:
            self.is_processing = False
            print("is_processing final",self.is_processing)
     
    def on_terminated(self, client, event: TerminationEvent):
       print(f"Session terminated: {event.audio_duration_seconds} seconds processed")
       # Process any remaining buffered transcript
       if self.transcript:
            self.process_buffered_transcript()     
    
    def on_error(self,client, error: StreamingError):
       print(f"Error: {error}")
       
    def stream(self, audio_chunk: bytes):
        self.client.stream(audio_chunk)
        

    def close(self):
        # Process any remaining transcript before closing
        if self.transcript:
            self.process_buffered_transcript()
        self.client.disconnect(terminate=True)   
    



   