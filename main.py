from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from murf import Murf
from dotenv import load_dotenv
import os

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


 







