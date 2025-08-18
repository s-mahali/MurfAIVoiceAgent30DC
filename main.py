from fastapi import FastAPI, UploadFile, HTTPException, WebSocket
from fastapi.websockets import WebSocketDisconnect
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from murf import Murf
from dotenv import load_dotenv
import os
import time
import assemblyai as aai
from google import genai
from services.murf_service import murf_tts
from services.assembly_service import AssemblyAIStreamingClient
import uuid
from services.socket import save_audio_chunk
import asyncio
import threading

load_dotenv()
MURF_API_KEY = os.getenv('MURF_API_KEY')
aai.settings.api_key =  os.getenv('ASSEMBLYAI_API_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

class Payload(BaseModel):
    text: str
    
    
@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.post("/audio", status_code=200)
async def generateAudio(payload: Payload):
    client = Murf(
       api_key = MURF_API_KEY
    )
    
    if not payload.text:
        raise HTTPException(status_code=400, detail="Missing text")
    res = client.text_to_speech.generate(
     text=payload.text,
     voice_id="en-US-Ken",
    
    )  
    
    if not res.audio_file:
        raise HTTPException(status_code=500, detail="No audio file generated")
    
    return res.audio_file   


@app.post('/upload/', status_code=200)
async def upload_file(file: UploadFile):
    try:
        # Create temp_upload directory if it doesn't exist
        os.makedirs("temp_upload", exist_ok=True)
        
        # Generate a unique filename
        timestamp = int(time.time())
        filename = f"temp_upload/{timestamp}_{file.filename if file.filename else 'recording.ogg'}"
        
        # Save the file to the temp_upload directory
        with open(filename, 'wb') as f:
            content = await file.read()
            f.write(content)
            print("File uploaded successfully to", filename)
        
        # Get file size in KB
        file_size = os.path.getsize(filename) / 1024
        
        return {
            "message": "File uploaded successfully",
            "filename": os.path.basename(filename),
            "content_type": file.content_type if file.content_type else "audio/ogg",
            "size_kb": round(file_size, 2)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
 
@app.post('/transcribe/file/', status_code=200)
async def transcribe_file(file: UploadFile):
    try:
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(file.file)
        print("transcript", transcript)
        # Handle missing or empty transcript text
        if not transcript or not getattr(transcript, "text", None) or not transcript.text.strip():
            return {"error": "Nothing to transcribe"}
        return {"transcript": transcript.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    #transcribe audio 
   

@app.post('/tts/echo/', status_code=200)
async def tts_echo(file: UploadFile):
    client = Murf(
       api_key = MURF_API_KEY
    )
    transcribe_text = transcription(file)
    print("transcribe_text", transcribe_text)
    
    if not file:
        raise HTTPException(status_code=400, detail="Missing file")
    if not isinstance(transcribe_text, dict) or "transcript" not in transcribe_text:
        return {"error": "Transcription failed"}
    res = client.text_to_speech.generate(
     text = transcribe_text["transcript"],
     voice_id="en-US-Ken",
    
    )  
    
    if not res.audio_file:
        raise HTTPException(status_code=500, detail="No audio file generated")
    print("audioURL: ",res.audio_file)
    return res.audio_file



@app.post('/llm/query', status_code=200)
async def llm_query(file: UploadFile):
    try:
        client = genai.Client()
        
        # assemblyAI transcribe 
        transcribed = transcription(file)
        print("transcription", transcribed)
        if not isinstance(transcribed, dict) or "transcript" not in transcribed:
            raise HTTPException(status_code=400, detail="Transcription failed")
        
        prompts = (
            "You are a helpful assistant that answers question.\n"
            "Keep answer within 2500 characters only.\n"
            f"question: {transcribed['transcript']}"
        )
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompts],
        )
        
        if response:
            answer_text = response.text
            if len(answer_text) > 3000:
                print(answer_text)
                answer_text = answer_text[:3000]
            # murfAI TTS
            murf_response = await murf_audio(answer_text)
            
            print("murf_response", murf_response)
            return murf_response
        else:
            return "Sorry! I don't have an answer for that."
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
#llm with history context 
#Dictionary to create or retrieve a session 
active_sessions = {}
#function to create or retrieve a session
def get_or_create_session(session_id: str):
    if session_id not in active_sessions:
        #create a new session with Gemini chat 
        client = genai.Client()
        chat = client.chats.create(model="gemini-2.5-flash")
        active_sessions[session_id] = {
            "chat": chat,
            "history": [
               { "role": "system",
                "content": "You are a helpful assistant that answers questions accurately and concisely."
               }
            ],
            "last_used": time.time()
        }
    else:
        #update last used timestamp
        active_sessions[session_id]["last_used"] = time.time()
    return active_sessions[session_id]        

@app.post('/agent/chat/{session_id}', status_code=200)
async def agent_chat(file: UploadFile, session_id: str):
    try:
        #get or create session
        session = get_or_create_session(session_id)
        chat = session["chat"]
        
        # assemblyAI transcribe 
        transcribed = transcription(file)
        print("transcription", transcribed)
        
        if not isinstance(transcribed, dict) or "transcript" not in transcribed:
              return JSONResponse(
                status_code=400,
                content={
                "audio": murf_response["audio_file"],
                "text": fallback_text,
                "error_type": "general_error",
                
                }
            )
        
        user_message = transcribed["transcript"]
        
        #add user_message to history
        session["history"].append({
            "role": "user",
            "content": user_message
        })
        response = chat.send_message(
            user_message
        )
        print("response1", response.text)
        
        if response.text:
            answer_text = response.text
            if len(answer_text) > 3000:
                print(answer_text)
                answer_text = answer_text[:3000]
                
            #add assistant_response to history
            session["history"].append({
                "role": "assistant",
                 "content": answer_text
            })    
            # murfAI TTS
            murf_response = await murf_tts(answer_text)
            
            print("murf_response", murf_response)
            return JSONResponse(
                status_code=200,
                content={
                    "audio": murf_response["audio_file"],
                    "text": answer_text,
                    "history": session["history"][-5:]
                }
            )
        else:
            #fallback
            fallback_text = "I'm having trouble processing your request. Please try again later."
            murf_response = await murf_tts(fallback_text)
            return JSONResponse(
                status_code=500,
                content={
                    "audio": murf_response["audio_file"],
                    "text": fallback_text,
                    
                    
                }
            )
    except Exception as e:
        # Graceful fallback on unexpected errors
        fallback_text = "I'm having trouble processing your request. Please try again later."
        murf_response = await murf_tts(fallback_text)
        return JSONResponse(
            status_code=500,
            content={
                "audio": murf_response["audio_file"],
                "text": fallback_text,
                
                }
        )
               
#websocket endpoint
# @app.websocket("/ws")
# async def websocket_endpoint(websocket: WebSocket):
#     await websocket.accept()
#     print("✅ websocket connection open")
#     session_id = str(uuid.uuid4())
#     file_path = None
#     aaiclient = client
#     if not connected:
#         await websocket.close(code=1011, reason="Failed to connect to transcription service")
#         return
#     try:
#         while True:
#          #receive the message
#          data = await websocket.receive_bytes()
#          print("receiving data")
#          if not data:
#              continue
         
#          #save the audio chunk
#          file_path = await save_audio_chunk(data, session_id)
         
         
         
         
         
#          #send acknowledgement back to the client
#          await websocket.send_json({"status": "received audio chunk", "session_id": session_id})
         
         
         
#     except WebSocketDisconnect:
#         print("❌websocket connection closed")
        
        
#     except Exception as e:
#         print("Error in websocket endpoint:", str(e))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket connection open")

    # Initialize AssemblyAI client 
    aaiClient = AssemblyAIStreamingClient(sample_rate=16000)
    try:
        while True:
            data = await websocket.receive_bytes()
            if not data:
                continue

            aaiClient.stream(data)
            await websocket.send_json({"status": "transcribing audio"})
    except WebSocketDisconnect:
        print("WebSocket disconnected")
    finally:
        aaiClient.close()
        print("AssemblyAI client disconnected")
    
        
    


        



