// const inputField = document.getElementById("inputField");
// const generateButton = document.getElementById("generateButton");
const audioPlayer = document.getElementById("audioPlayer");
const recordButton = document.getElementById("recordButton");
const stopRecordButton = document.getElementById("stopButton");
const recordingPlayer = document.getElementById("recordingPlayer");
const recorderContainer = document.getElementById("recorderContainer");
const fileName = document.getElementById("filename");
const contentType = document.getElementById("contentType");
const fileSize = document.getElementById("sizeKb");
const resultContainer = document.getElementById("resultContainer");
const trContainer = document.getElementById("trContainer");
const transcriptElem = document.getElementById("transcript");
const llmLoading = document.getElementById("llmLoading");
const botListening = document.getElementById("botListening");
const botSpeaking = document.getElementById("botSpeaking");
const errorContainer = document.getElementById("errorContainer");
const errorText = document.getElementById("errorText");
//const chatWindow = document.getElementById("chatWindow");
const streamingUI = document.getElementById("streamingStatus");
const transcriptSection = document.getElementById("transcriptSection");

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


//Function to queue and play audio chunks
function queueAudioForPlayback(base64Data) {
  if (!streamAudioContext) {
    streamAudioContext = new window.AudioContext({ sampleRate: 44100 });
    playheadTime = streamAudioContext.currentTime;
    botSpeaking.classList.add("active");
  }

  try {
    //store base64 chunks for debugging
    base64AudioChunks.push(base64Data);
    //convert base64 to PCM FLoat32
    const pcmData = base64ToPCMFloat32(base64Data);

    if (pcmData) {
      console.log("converted base64 to pcm");
      audioChunks.push(pcmData);

      if (!isPlaying) {
        playAudioChunks();
      }
    }
  } catch (error) {
    console.error("Error processing base64 audio:", error);
  }
}

//Function to base64ToPCMFLoat32
function base64ToPCMFloat32(base64) {
  const binary = atob(base64);
  const offset = wavHeaderStripped ? 0 : 44;
  console.log("offset", offset);
  if (!wavHeaderStripped && binary.length > 44) {
    console.log("wavheader");
    wavHeaderStripped = true;
  }
  const length = binary.length - offset;
  if (length <= 0) return null;

  const bytes = new Uint8Array(length);
  for (let i = 0; i < length; i++) {
    bytes[i] = binary.charCodeAt(i + offset);
  }

  const sampleCount = bytes.length / 2;
  const float32Array = new Float32Array(sampleCount);
  const dataView = new DataView(bytes.buffer);
  for (let i = 0; i < sampleCount; i++) {
    const int16 = dataView.getInt16(i * 2, true);
    float32Array[i] = Math.max(-1, Math.min(1, int16 / 32768)); // Convert to float32
    
  }

  return float32Array;
}


function playAudioChunks() {
  if (audioChunks.length === 0) {
    isPlaying = false;
    wavHeaderStripped = false;
    botSpeaking.classList.remove("active");
    return;
  }

  isPlaying = true;
  const chunk = audioChunks.shift();

  if (streamAudioContext.state === "suspended") {
    streamAudioContext.resume();
  }

  const buffer = streamAudioContext.createBuffer(1, chunk.length, 44100);
  buffer.copyToChannel(chunk, 0);

  const source = streamAudioContext.createBufferSource();
  source.buffer = buffer;
  source.connect(streamAudioContext.destination);

  const now = streamAudioContext.currentTime;
  // if (playheadTime < now) {
  //     playheadTime = now + 0.05;
  // }
  console.log("playing at");
  source.start(0);
  playheadTime += buffer.duration;

  source.onended = () => {
    if (audioChunks.length > 0) {
      playAudioChunks();
    } else {
      isPlaying = false;
      wavHeaderStripped = false;
      botSpeaking.classList.remove("active");
    }
  };
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
  botSpeaking.classList.remove("active");
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
    //handle server acknowledgement here
    const data = JSON.parse(event.data);
    //console.log("transcript:", event.data);
    // if(data.status === "final_transcript") {
    //         //create a p element to display the transcript
    //         const p = document.createElement("p");
    //         p.innerText = data.transcript;
    //         transcriptSection.appendChild(p);
    //     }

    if (data.status === "audio_chunk") {
      console.log("audio chunk 🔊 ");
      queueAudioForPlayback(data.audio_base64);
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

/* 🔹 Convert Float32 → PCM16 */
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

if (navigator.mediaDevices) {
  console.log("mediaDevices", navigator.mediaDevices);
}

recordButton.onclick = async () => {
  websocket = setupWebSocket();
  isRecording = true;
  recordButton.disabled = true;
  botListening.classList.add("active");

  // Set up Web Audio API for PCM16 streaming
  audioContext = new (window.AudioContext || window.webkitAudioContext)({
    sampleRate: 16000,
  });
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
};

stopRecordButton.onclick = () => {
  isRecording = false;
  recordButton.disabled = false;
  botListening.classList.remove("active");
  if (scriptProcessor) scriptProcessor.disconnect();
  if (source) source.disconnect();
  if (audioContext) audioContext.close();
  if (websocket && websocket.readyState === WebSocket.OPEN) {
    websocket.close();
  }
  cleanupStreamAudio();
};

const uploadingContainer = document.getElementById("uploadingContainer");
const uploadingText = document.getElementById("uploadingText");
const uploadingPercentage = document.getElementById("uploadingPercentage");

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
      botSpeaking.classList.add("active");

      recordingPlayer.src = data.audio;
      //recordingPlayer.classList.add("show");
      recordingPlayer.onplay = () => {
        botSpeaking.classList.add("active");
      };

      recordingPlayer.onended = () => {
        botSpeaking.classList.remove("active");
      };
      recordingPlayer.play();
    } else {
      if (data.audio) {
        recordingPlayer.src = data.audio;
        recordingPlayer.onplay = () => {
          botSpeaking.classList.add("active");
        };
        recordingPlayer.onended = () => {
          botSpeaking.classList.remove("active");
        };
        recordingPlayer.play();
      }
      errorContainer.style.display = "flex";
      errorText.innerText = `Error: ${
        data.text || "An unexpected error occurred."
      }`;
    }
  } catch (error) {
    console.error("error fetching llm response:", error?.message);
    // llmLoading.classList.remove("show");
    recordButton.disabled = false;
    stopRecordButton.disabled = false;
    botListening.classList.remove("active");
    botSpeaking.classList.remove("active");
    errorContainer.style.display = "flex";
    errorText.innerText = `Error: I'm having trouble processing your request. Please try again later.`;
  } finally {
    // --- Hide loading state and re-enable buttons ---
    llmLoading.classList.remove("show");
    recordButton.disabled = false;
    stopRecordButton.disabled = false;
    botListening.classList.remove("active");
  }
};
