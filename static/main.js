const inputField = document.getElementById("inputField");
const generateButton = document.getElementById("generateButton");
const audioPlayer = document.getElementById("audioPlayer");
const recordButton = document.getElementById("recordButton");
const stopRecordButton = document.getElementById("stopButton");
const recordingPlayer = document.getElementById("recordingPlayer");
const recorderContainer = document.getElementById("recorderContainer");
console.log("recordButton", recordButton);

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
      alert("record stopped!");
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
      recordingPlayer.play();
      console.log("recorder stopped");
    };

    mediaRecorder.ondataavailable = (e) => {
      chunks.push(e.data);
    };
  })
  .catch((err) => {
    console.error(`The following error occurred: ${err}`);
  });
