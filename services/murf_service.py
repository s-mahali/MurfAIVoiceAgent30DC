import os
from murf import Murf
from dotenv import load_dotenv

load_dotenv()
MURF_API_KEY = os.getenv('MURF_API_KEY')


    
    
# murf service 
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
