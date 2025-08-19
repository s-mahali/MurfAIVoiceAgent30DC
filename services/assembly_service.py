from fastapi import UploadFile
import assemblyai as aai
from dotenv import load_dotenv
import os
import asyncio
import logging
from typing import Type
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
    def __init__(self, websocket, loop, sample_rate=16000):
        self.websocket = websocket
        self.loop = loop
        
        self.client = StreamingClient(
            StreamingClientOptions(
                api_key= aai.settings.api_key,
                api_host= "streaming.assemblyai.com"
                
            )
        )
        self.client.on(StreamingEvents.Begin, self.on_begin)
        self.client.on(StreamingEvents.Turn, self.on_turn)
        self.client.on(StreamingEvents.Termination, self.on_terminated)
        self.client.on(StreamingEvents.Error, self.on_error)
        
        self.client.connect(StreamingParameters(
            sample_rate=sample_rate, format_turns=False
        ))
    
    def on_begin(self, client, event: BeginEvent):
       print(f"Session started: {event.id}")
    
    def on_turn(self, client, event: TurnEvent):
      # Print transcripts as they arrive
      print(f"{event.transcript} (end_of_turn={event.end_of_turn})")
      if event.end_of_turn:
          try:
              asyncio.run_coroutine_threadsafe(
                  self.websocket.send_json({
                      "status": "final_transcript",
                      "transcript": event.transcript,
                      "end_of_turn": event.end_of_turn
                  }),
                  self.loop
              )
          except Exception as e:
              logging.error("Error sending transcript: %s", e)
      
      
      if event.end_of_turn and not event.turn_is_formatted:
         client.set_params(StreamingSessionParameters(format_turns=True))
     
    def on_terminated(self, client, event: TerminationEvent):
       print(f"Session terminated: {event.audio_duration_seconds} seconds processed")     
    
    def on_error(self, error: StreamingError):
       print(f"Error: {error}")
       
    def stream(self, audio_chunk: bytes):
        self.client.stream(audio_chunk)

    def close(self):
        self.client.disconnect(terminate=True)    
    
    