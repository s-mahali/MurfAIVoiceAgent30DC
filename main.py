from fastapi import FastAPI, UploadFile
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from murf import Murf
from dotenv import load_dotenv
import os
import time

load_dotenv()
MURF_API_KEY = os.getenv('MURF_API_KEY')


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
 







