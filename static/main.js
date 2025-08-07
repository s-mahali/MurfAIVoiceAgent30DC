const inputField = document.getElementById("inputField");
const generateButton = document.getElementById("generateButton");
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

let content = "";

async function fetchAudioContent(e) {
  e.preventDefault();
  try {
    content = inputField.value;
    console.log("content:", content);
    const response = await fetch("/audio", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ text: content }),
    });
    if (response) {
      const audioResponse = await response.json();
      audioPlayer.src = audioResponse;
      audioPlayer.play();
      inputField.value = "";
    }
  } catch (error) {
    console.error("error fetching audio content:", error?.message);
  }
}

generateButton.addEventListener("click", fetchAudioContent);

//Day-4
if (navigator.mediaDevices) {
  console.log("mediaDevices", navigator.mediaDevices);
}

const constraints = { audio: true };
let chunks = [];

navigator.mediaDevices
  .getUserMedia(constraints)
  .then((stream) => {
    const mediaRecorder = new MediaRecorder(stream);

    recordButton.onclick = () => {
      console.log("clicked");
      mediaRecorder.start();
      console.log("started recording", mediaRecorder.state);
      recordButton.style.background = "red";
      recordButton.innerText = "Recording in Progress";
      recordButton.disabled = true;
      recordButton.style.cursor = "not-allowed";
      recordButton.style.color = "black";
    };

    stopRecordButton.onclick = () => {
      mediaRecorder.stop();
      console.log("stopped recording", mediaRecorder.state);
      recordButton.style.background = "green";
      recordButton.disabled = false;
      recordButton.style.cursor = "pointer";
      recordButton.style.color = "";
      recordButton.style.background = "";
      stopRecordButton.style.color = "black";
      recordButton.textContent = "Record Audio";
    };

    mediaRecorder.onstop = (e) => {
      console.log("data available after MediaRecorder.stop() called.");

      const blob = new Blob(chunks, { type: "audio/ogg; codecs = opus" });
      chunks = [];
      const audioURL = URL.createObjectURL(blob);
      recordingPlayer.src = audioURL;

      // Upload Audio File to server temp_upload folder
      //uploadAudioFile(blob);
      try {
        transcribeFile(blob);
      } catch (error) {
        console.error("error transcribing audio file:", error?.message);
      }

      console.log("recorder stopped");
    };

    mediaRecorder.ondataavailable = (e) => {
      chunks.push(e.data);
    };
  })
  .catch((err) => {
    console.error(`The following error occurred: ${err}`);
  });

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
  uploadingContainer.style.display = "flex";
  uploadingText.innerText = "Transcribing your audio file...";
  uploadingPercentage.innerText = "";
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
      trContainer.style.display = "flex";
      transcriptElem.innerText = `Transcript: ${data.transcript}`;
    }

    // Hide the transcribing message after 2 seconds
    setTimeout(() => {
      uploadingContainer.style.display = "none";
    }, 3000);
  } catch (error) {
    console.error("Error transcribing audio file:", error?.message);
    // Just hide the message on error, no error displayed to user
    setTimeout(() => {
      uploadingContainer.style.display = "none";
    }, 1000);
  } 
};

// Just completed a voice-to-text transcription feature in my voice agent using FastAPI and JavaScript MediaRecorder. The app now seamlessly captures audio, sends it to the server, and returns a clean transcript with a simple user experience.