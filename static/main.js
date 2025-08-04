const inputField = document.getElementById("inputField");
const generateButton = document.getElementById("generateButton");
const audioPlayer = document.getElementById("audioPlayer");

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
    })
    if(response) {
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
