from fastapi import FastAPI, UploadFile
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from murf import Murf
from dotenv import load_dotenv
import os
import time
import assemblyai as aai
from google import genai



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

@app.post("/audio")
async def generateAudio(payload: Payload):
    client = Murf(
       api_key = MURF_API_KEY
    )
    
    if not payload.text:
        return {"error": "No text provided"}
    res = client.text_to_speech.generate(
     text=payload.text,
     voice_id="en-US-Ken",
    
    )  
    
    if not res.audio_file:
        return {"error": "No audio file generated"}
    
    return res.audio_file   


@app.post('/upload/')
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
        print("Error uploading file:", str(e))
        return {"error": str(e)}
 
@app.post('/transcribe/file/')
async def transcribe_file(file: UploadFile):
    try:
        transcriber = aai.Transcriber()
        transcript =  transcriber.transcribe(file.file)
        print("transcript",transcript)
        return {"transcript": transcript.text}
    except Exception as e:
        return {"error": str(e)}
    
    #transcribe audio 
def transcription(file: UploadFile):
    try:
        transcriber = aai.Transcriber()
        transcript =  transcriber.transcribe(file.file)
        print("transcript",transcript)
        return {"transcript": transcript.text}
    except Exception as e:
        print("Error uploading file:", str(e))
        return {"error": str(e)}    

@app.post('/tts/echo/')
async def tts_echo(file: UploadFile):
    client = Murf(
       api_key = MURF_API_KEY
    )
    transcribe_text = transcription(file)
    print("transcribe_text", transcribe_text)
    
    if not file:
        return {"error": "Missing text or file"}
    if not isinstance(transcribe_text, dict) or "transcript" not in transcribe_text:
        return {"error": "Transcription failed"}
    res = client.text_to_speech.generate(
     text = transcribe_text["transcript"],
     voice_id="en-US-Ken",
    
    )  
    
    if not res.audio_file:
        return {"error": "No audio file generated"}
    print("audioURL: ",res.audio_file)
    return res.audio_file

# murf service 
async def murf_audio(text: str):
    client = Murf(
       api_key = MURF_API_KEY
    )
    
    if not text:
        return {"error": "No text provided"}
    res = client.text_to_speech.generate(
     text=text,
     voice_id="en-US-Ken",
    
    )  
    
    if not res.audio_file:
        return {"error": "No audio file generated"}
    
    return res.audio_file

@app.post('/llm/query')
async def llm_query(file: UploadFile):
    try:
        client = genai.Client()
        
        # assemblyAI transcribe 
        transcribed = transcription(file)
        print("transcription", transcribed)
        if not isinstance(transcribed, dict) or "transcript" not in transcribed:
            return {"error": "Transcription failed"}
        
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
        return {"error": str(e)}
    
#Day 10 llm with history context 

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

@app.post('/agent/chat/{session_id}')
async def agent_chat(file: UploadFile, session_id: str):
    try:
        #get or create session
        session = get_or_create_session(session_id)
        chat = session["chat"]
        
        # assemblyAI transcribe 
        transcribed = transcription(file)
        print("transcription", transcribed)
        
        if not isinstance(transcribed, dict) or "transcript" not in transcribed:
            return {"error": "Transcription failed"}
        
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
        
        if response:
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
            murf_response = await murf_audio(answer_text)
            
            print("murf_response", murf_response)
            return murf_response
        else:
            return {"error": "Sorry! No response from assistant."}
    except Exception as e:
        return {"error": str(e)}
    


        



