// UI elements
const recordButton = document.getElementById("recordButton");
const stopRecordButton = document.getElementById("stopButton");
const recordingPlayer = document.getElementById("recordingPlayer");
const llmLoading = document.getElementById("llmLoading");
const botSpeaking = document.getElementById("botSpeaking");
const errorContainer = document.getElementById("errorContainer");
const errorText = document.getElementById("errorText");
const chatWindow = document.getElementById("chatWindow");
const pulseRing = document.getElementById("pulseRing");
const statusText = document.getElementById("statusText");
const thoughtsDisplay = document.getElementById("thoughtsDisplay");
const resumeButton = document.getElementById("resumeButton");
const restartButton = document.getElementById("restartButton");

let content = "";

//streaming websocket setup
let websocket = null;
let isRecording = false;
let audioContext;
let scriptProcessor;
let source;
let streamAudioContext = null;
let audioChunks = [];
let base64AudioChunks = [];
let playheadTime = 0;
let wavHeaderStripped = false;
let isPlaying = false;

//Function to base64ToPCMFLoat32
function base64ToPCMFloat32(base64) {
  const binary = atob(base64);
  let offset = 0;
  console.log("offset", offset);
  if (
    !wavHeaderStripped &&
    binary.length > 44 &&
    binary.slice(0, 4) === "RIFF"
  ) {
    console.log("Detected WAV header, stripping 44 bytes");
    offset = 44;
    wavHeaderStripped = true;
  }
  const length = binary.length - offset;
  if (length <= 0) return null;

  const bytes = new Uint8Array(length);
  for (let i = 0; i < length; i++) {
    bytes[i] = binary.charCodeAt(i + offset);
  }

  const dataView = new DataView(bytes.buffer);
  const sampleCount = bytes.length / 2;
  const float32Array = new Float32Array(sampleCount);

  for (let i = 0; i < sampleCount; i++) {
    const int16 = dataView.getInt16(i * 2, true);
    float32Array[i] = int16 / 32768;
    // Convert to float32
  }

  return float32Array;
}

//play audio
function playAudioChunks(base64Audio) {
  if (!streamAudioContext) {
    streamAudioContext = new (window.AudioContext || window.webkitAudioContext)(
      { sampleRate: 44100 }
    );
    playheadTime = streamAudioContext.currentTime;

    pulseRing.classList.add("speaking");
    statusText.textContent = "Speaking";
    pulseRing.classList.remove("listening");
  }

  const float32Array = base64ToPCMFloat32(base64Audio);
  if (!float32Array) return;

  //create audio buffer
  const buffer = streamAudioContext.createBuffer(1, float32Array.length, 44100);
  buffer.copyToChannel(float32Array, 0);
  const source = streamAudioContext.createBufferSource();
  source.buffer = buffer;
  source.connect(streamAudioContext.destination);
  const now = streamAudioContext.currentTime;
  if (playheadTime < now + 0.15) {
    playheadTime = now + 0.15;
  }
  source.start(playheadTime);
  playheadTime += buffer.duration;
  isPlaying = true;
}

// Cleanup function when stopping
function cleanupStreamAudio() {
  audioChunks = [];
  base64AudioChunks = [];
  isPlaying = false;
  wavHeaderStripped = false;
  if (streamAudioContext) {
    streamAudioContext.close();
    streamAudioContext = null;
  }

  // Reset UI when audio playback is complete
  pulseRing.classList.remove("speaking");
  statusText.textContent = "Meow";
  updateThoughtsDisplay("idle");
}

function setupWebSocket() {
  // Set up WebSocket connection
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const wsUrl = `${protocol}://${window.location.host}/ws`;
  websocket = new WebSocket(wsUrl);

  console.log("WebSocket URL:", wsUrl);

  websocket.onopen = () => {
    console.log("WebSocket connection established");
  };

  websocket.onmessage = (event) => {
    // Handle server acknowledgement here
    const data = JSON.parse(event.data);

    if (data.status === "transcript") {
      console.log("transcript received:", data.transcript);
      // Add user message to chat
      addMessageToChat(data.transcript, "user");
      // Update status to processing
      updateThoughtsDisplay("processing");
    } else if (data.status === "bot_speaking") {
      // Pause mic streaming while bot speaks; resume when inactive
      const active = !!data.active;
      if (active) {
        pulseRing.classList.remove("listening");
        pulseRing.classList.add("speaking");
        statusText.textContent = "Speaking";
        updateThoughtsDisplay("speaking");
      } else {
        pulseRing.classList.remove("speaking");
        statusText.textContent = "Meow";
        updateThoughtsDisplay("idle");
      }
    } else if (data.status === "audio_chunk") {
      playAudioChunks(data.audio_base64);
    } else if (data.status === "audio_complete") {
      // Allow user to continue speaking without restarting session
      console.log("audio complete ✅");
    } else if (data.status === "llm_response") {
      // Add bot message to chat
      addMessageToChat(data.text, "assistant");
    }
  };

  websocket.onclose = () => {
    console.log("WebSocket connection closed");
  };

  websocket.onerror = (error) => {
    console.error("WebSocket error:", error);
    errorContainer.style.display = "flex";
    errorText.innerText = `WebSocket Error: Connection failed`;
  };

  return websocket;
}

/*  Convert Float32 → PCM16 */
function floatTo16BitPCM(float32Array) {
  const buffer = new ArrayBuffer(float32Array.length * 2);
  const view = new DataView(buffer);
  let offset = 0;
  for (let i = 0; i < float32Array.length; i++, offset += 2) {
    let s = Math.max(-1, Math.min(1, float32Array[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return buffer;
}

// Update thoughts display based on current state
function updateThoughtsDisplay(state) {
  switch (state) {
    case "idle":
      thoughtsDisplay.textContent = "your thoughts...";
      thoughtsDisplay.classList.remove(
        "listening",
        "processing",
        "speaking",
        "error"
      );
      break;
    case "listening":
      thoughtsDisplay.textContent = "listening to your thoughts...";
      thoughtsDisplay.classList.add("listening");
      thoughtsDisplay.classList.remove("processing", "speaking", "error");
      break;
    case "processing":
      thoughtsDisplay.textContent = "processing your thoughts...";
      thoughtsDisplay.classList.add("processing");
      thoughtsDisplay.classList.remove("listening", "speaking", "error");
      break;
    case "speaking":
      thoughtsDisplay.textContent = "responding to your thoughts...";
      thoughtsDisplay.classList.add("speaking");
      thoughtsDisplay.classList.remove("listening", "processing", "error");
      break;
    case "error":
      thoughtsDisplay.textContent = "there was an error...";
      thoughtsDisplay.classList.remove("listening", "processing", "speaking");
      thoughtsDisplay.classList.add("error");
      break;
  }
}

if (navigator.mediaDevices) {
  console.log("mediaDevices", navigator.mediaDevices);
}

// Add a message to the chat window
function addMessageToChat(text, sender) {
  const messageEl = document.createElement("div");
  messageEl.classList.add("message", sender);
  messageEl.textContent = text;
  chatWindow.appendChild(messageEl);

  // Scroll to the bottom
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

recordButton.onclick = async () => {
  if (!websocket || websocket.readyState !== WebSocket.OPEN) {
    websocket = setupWebSocket();
  }

  isRecording = true;
  recordButton.style.display = "none";
  stopRecordButton.style.display = "flex";

  // Update UI status
  pulseRing.classList.add("listening");
  statusText.textContent = "Listening";
  updateThoughtsDisplay("listening");

  // Set up Web Audio API for PCM16 streaming
  if (!audioContext) {
    audioContext = new (window.AudioContext || window.webkitAudioContext)({
      sampleRate: 16000,
    });

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      source = audioContext.createMediaStreamSource(stream);
      scriptProcessor = audioContext.createScriptProcessor(4096, 1, 1);

      scriptProcessor.onaudioprocess = (audioProcessingEvent) => {
        if (!isRecording) return;
        const inputData = audioProcessingEvent.inputBuffer.getChannelData(0);
        const pcm16Buffer = floatTo16BitPCM(inputData);
        if (websocket && websocket.readyState === WebSocket.OPEN) {
          websocket.send(pcm16Buffer);
        }
      };

      source.connect(scriptProcessor);
      scriptProcessor.connect(audioContext.destination);
    } catch (error) {
      console.error("Error accessing microphone:", error);
      errorContainer.style.display = "flex";
      errorText.innerText =
        "Error accessing microphone. Please check permissions.";
      updateThoughtsDisplay("error");

      // Reset UI
      recordButton.style.display = "flex";
      stopRecordButton.style.display = "none";
      pulseRing.classList.remove("listening");
      statusText.textContent = "Error";
      
    }
  } else {
    // Resume existing audio context
    if (audioContext.state === "suspended") {
      await audioContext.resume();
    }
  }
};

stopRecordButton.onclick = () => {
  isRecording = false;
  stopRecordButton.style.display = "none";
  recordButton.style.display = "flex";
  recordButton.disabled = false;

  // Update UI status
  pulseRing.classList.remove("listening");
  statusText.textContent = "Processing";

  if (scriptProcessor) scriptProcessor.disconnect();
  if (source) source.disconnect();
  if (audioContext) audioContext.close();
  if (websocket && websocket.readyState === WebSocket.OPEN) {
    websocket.close();
  }
  cleanupStreamAudio();
};

document.addEventListener("DOMContentLoaded", () => {
  stopRecordButton.style.display = "none";

  errorContainer.style.display = "none";

  addMessageToChat("Hello! How can I help you today?", "assistant");

  statusText.textContent = "Meow";
  updateThoughtsDisplay("idle");

  resumeButton.addEventListener("click", () => {
    recordButton.click();
  });
});

// const uploadAudioFile = async (file) => {
//   try {
//     // Show uploading status
//     uploadingContainer.style.display = "flex";
//     uploadingText.innerText = "Uploading audio file...";
//     uploadingPercentage.innerText = "0%";

//     const formData = new FormData();
//     formData.append("file", file, "recording.ogg");

//     // Use fetch with XMLHttpRequest to track upload progress
//     const xhr = new XMLHttpRequest();

//     // Track upload progress
//     xhr.upload.onprogress = (event) => {
//       if (event.lengthComputable) {
//         const percentComplete = Math.round((event.loaded / event.total) * 100);
//         uploadingPercentage.innerText = percentComplete + "%";
//       }
//     };

//     // Create a promise to handle the response
//     const uploadPromise = new Promise((resolve, reject) => {
//       xhr.onload = () => {
//         if (xhr.status >= 200 && xhr.status < 300) {
//           resolve(JSON.parse(xhr.responseText));
//         } else {
//           reject(new Error(`HTTP Error: ${xhr.status}`));
//         }
//       };
//       xhr.onerror = () => reject(new Error("Network Error"));
//     });

//     // Send the request
//     xhr.open("POST", "/upload", true);
//     xhr.send(formData);

//     // Wait for the response
//     const responseData = await uploadPromise;
//     console.log("Upload successful:", responseData);

//     // Update UI with file details
//     resultContainer.style.display = "flex";
//     fileName.innerText = `Filename: ${responseData.filename}`;
//     contentType.innerText = `Content Type: ${responseData.content_type}`;
//     fileSize.innerText = `File Size: ${responseData.size_kb} KB`;
//     uploadingText.innerText = `Upload complete!`;
//     uploadingPercentage.innerText = "";

//     // Hide only upload status after 3 seconds
//     setTimeout(() => {
//       uploadingContainer.style.display = "none";
//     }, 3000);
//        return responseData;
//   } catch (error) {
//     console.error("error uploading audio file:", error?.message);
//     uploadingText.innerText =
//       "Upload failed: " + (error?.message || "Unknown error");
//     uploadingPercentage.innerText = "";

//     // Hide only upload status after 3 seconds
//     setTimeout(() => {
//       uploadingContainer.style.display = "none";
//     }, 3000);
//   }
// };

const transcribeFile = async (file) => {
  // uploadingContainer.style.display = "flex";
  // uploadingText.innerText = "Transcribing your audio file...";
  // uploadingPercentage.innerText = "";
  try {
    const formData = new FormData();
    formData.append("file", file, "recording.ogg");

    const response = await fetch("/transcribe/file", {
      method: "POST",
      body: formData,
    });

    if (response.ok) {
      const data = await response.json();
      // Very simple UI update with just the transcript
      // trContainer.style.display = "flex";
      // transcriptElem.innerText = `Transcript: ${data.transcript}`;
      return data.transcript;
    }

    // Hide the transcribing message after 2 seconds
    // setTimeout(() => {
    //   uploadingContainer.style.display = "none";
    // }, 3000);
  } catch (error) {
    console.error("Error transcribing audio file:", error?.message);
    // Just hide the message on error, no error displayed to user
    // setTimeout(() => {
    //   uploadingContainer.style.display = "none";
    // }, 1000);
  }
};

//playback your audio through murf tts
const murfAudioPlayback = async (file) => {
  try {
    const formData = new FormData();
    formData.append("file", file, "recording.ogg");

    const response = await fetch("/tts/echo", {
      method: "POST",
      body: formData,
    });
    if (response.ok) {
      const data = await response.json();
      console.log("data:", data);
      recordingPlayer.src = data;
      recordingPlayer.play();
    }
  } catch (error) {
    console.error("error fetching audio content:", error?.message);
  }
};

const fetchResponsefromllm = async (file) => {
  console.log("fetching response from llm...");
  // --- Show loading state and disable buttons ---
  llmLoading.classList.add("show");
  statusText.textContent = "Processing";
  recordingPlayer.classList.remove("show"); // Hide previous player
  recordButton.disabled = true;
  stopRecordButton.disabled = true;
  let sessionId = localStorage.getItem("sessionId");
  if (!sessionId) {
    sessionId = Date.now().toString();
    localStorage.setItem("sessionId", sessionId);
  }

  console.log("fetching response from llm with session:", sessionId);
  try {
    const formData = new FormData();
    formData.append("file", file, "recording.ogg");

    const response = await fetch(`/agent/chat/${sessionId}`, {
      method: "POST",
      body: formData,
    });
    if (response.ok) {
      const data = await response?.json();
      console.log("data:", data);

      pulseRing.classList.add("speaking");
      statusText.textContent = "Speaking";

      // Add assistant response to chat window
      if (data.text) {
        addMessageToChat(data.text, "assistant");
      }

      recordingPlayer.src = data.audio;
      recordingPlayer.onplay = () => {
        pulseRing.classList.add("speaking");
        statusText.textContent = "Speaking";
      };

      recordingPlayer.onended = () => {
        pulseRing.classList.remove("speaking");
        statusText.textContent = "Poised";
      };
      recordingPlayer.play();
    } else {
      if (data && data.audio) {
        recordingPlayer.src = data.audio;
        recordingPlayer.onplay = () => {
          pulseRing.classList.add("speaking");
        };
        recordingPlayer.onended = () => {
          pulseRing.classList.remove("speaking");
        };
        recordingPlayer.play();
      }

      // Show error message
      errorContainer.style.display = "flex";
      errorText.innerText = `Error: ${
        (data && data.text) || "An unexpected error occurred."
      }`;
      statusText.textContent = "Error";
    }
  } catch (error) {
    console.error("error fetching llm response:", error?.message);
    recordButton.disabled = false;
    stopRecordButton.style.display = "none";
    recordButton.style.display = "flex";
    botListening.classList.remove("active");

    pulseRing.classList.remove("listening");
    pulseRing.classList.remove("speaking");
    errorContainer.style.display = "flex";
    errorText.innerText = `Error: I'm having trouble processing your request. Please try again later.`;
    statusText.textContent = "Error";
  } finally {
    // --- Hide loading state and re-enable buttons ---
    llmLoading.classList.remove("show");
    recordButton.disabled = false;
    stopRecordButton.disabled = false;
    stopRecordButton.style.display = "none";
    recordButton.style.display = "flex";
    botListening.classList.remove("active");
  }
};

// Add event listener for restart button
restartButton.addEventListener("click", () => {
  // Clear session ID to start fresh
  localStorage.removeItem("sessionId");
  // Clear chat messages
  chatWindow.innerHTML = "";
  pulseRing.classList.remove("listening");
  pulseRing.classList.remove("speaking");
  statusText.textContent = "Meow";

  // Add welcome message
  addMessageToChat("Hello! How can I help you today?", "assistant");
});
