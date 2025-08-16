from fastapi import UploadFile
import assemblyai as aai
from dotenv import load_dotenv
import os

load_dotenv()
aai.settings.api_key =  os.getenv('ASSEMBLYAI_API_KEY')
def transcription(file: UploadFile):
    try:
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(file.file)
        # Handle missing or empty transcript text
        if not transcript or not getattr(transcript, "text", None) or not transcript.text.strip():
            return {"error": "Nothing to transcribe"}
        print("transcript", transcript)
        return {"transcript": transcript.text}
    except Exception as e:
        print("Error uploading file:", str(e))
        return {"error": str(e)} 