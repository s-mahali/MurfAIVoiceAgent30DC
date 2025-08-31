# Murf AI Voice Agent 30DC 🎙️🤖

A conversational **voice-first AI assistant** web app that enables real-time, voice-based interaction between users and an AI agent.  
Users talk to the agent via microphone → speech is transcribed → processed by an LLM → the response is converted back into speech with **Murf AI TTS**.  

Now live at:  
👉 [Deployed App on Render](https://murfaivoiceagent30dc.onrender.com/)

---

## ✨ Features
- 🎤 **Voice-based chat** with AI assistant
- 🧠 **Session-based conversation management** for maintaining context
- 🔊 **Audio playback** for both user and bot messages
- ⚙️ **Config panel** in UI to add your own API keys dynamically
- 🔗 **Tool calling support**
  - Web search tool
  - Ticket creation tool
- 📱 Modern, responsive UI (works on desktop & mobile)

---

## 🏗️ Architecture
- **Client (Frontend)**
  - Single-page web app (HTML, CSS, JS)
  - Chat UI with text + audio bubbles
  - Config section for user-provided API keys

- **Server (Backend - FastAPI)**
  - Handles audio recording & uploads
  - Transcribes voice input (AssemblyAI)
  - Sends transcript to Gemini LLM for reasoning
  - Calls tools when needed (web search, ticket creation)
  - Generates bot speech output (Murf AI TTS)
  - Returns **both text + audio** responses to frontend

---

## 🛠️ Technologies Used
- **Frontend:** HTML, CSS, JavaScript
- **Backend:** Python (FastAPI)
- **Audio Processing:** Web Audio API, MediaRecorder
- **APIs & AI Services:**
  - [Google Gemini](https://ai.google/) → LLM
  - [Murf AI](https://murf.ai/) → Text-to-Speech
  - [AssemblyAI](https://www.assemblyai.com/) → Speech-to-Text
  - Custom Tool-Calling (Web + Ticket System)

---

## 📸 Screenshots
![Screenshot 1](./screenshots/ss1.png)
![Screenshot 2](./screenshots/ss2.png)

---

## 🚀 Getting Started

### 1. Clone the repository
```sh
git clone https://github.com/s-mahali/MurfAIVoiceAgent30DC.git
cd Murf30Days
```

### 2. Setup Virtual Environment
```sh
    python -m venv .venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # macOS/Linux
```
### 3. Install dependencies
```sh
   pip install -r requirements.txt
```

### 4. Set up API Keys
Create a .env file in the root directory with the following content:
```MURF_API_KEY=your_murf_api_key
   ASSEMBLYAI_API_KEY=your_assemblyai_api_key
   GEMINI_API_KEY=your_google_api_key
   TAVILY_API_KEY=your_tavily_api_key
```
Or enter keys in the config panel in the UI.

### 5. Run the application
```sh
   uvicorn main:app --reload
```

### 6. Open in browser
Navigate to `http://127.0.0.1:8000/` to open the application.


### 🔌API Endpoints:
 ws/ → WebSocket for real-time voice chat
POST /transcribe/file → Transcribe uploaded audio
POST /agent/chat/{session_id} → Conversational AI (voice in, bot voice/text out)
POST /tts/echo → Convert text to speech (Murf TTS)
Tool APIs integrated for Web Search & Ticket Creation

---

### 💰 API Free Tier & Rate Limits

Murf AI: $3 free credit, $0.03 / 1,000 characters, concurrency limit = 5
AssemblyAI: Free trial available, billed per minute of audio
Gemini: Generous free tier, subject to Google’s limits
Tavily: Free tier available, 1000 requests/month

### 📂 Folder Structure
```sh
main.py
readme.md
config/
   config.py
services/
   assemblyai_service.py
   gemini_service.py
   murf_service.py
   tool_calling.py
.env
requirements.txt
static/
   index.html
   main.js
   style.css
   robot.png
screenshots/
   ss1.png
   ss2.png
```   
---

### 📜 License
MIT License

### 🔗 Live Demo
👉 https://murfaivoiceagent30dc.onrender.com/