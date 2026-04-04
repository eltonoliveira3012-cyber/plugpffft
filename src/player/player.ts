const audio = new Audio();
audio.preload = "auto";
audio.volume = 1;

window.plugPffft.onPlaySound(async (audioUrl: string) => {
  try {
    audio.pause();
    audio.currentTime = 0;
    audio.src = audioUrl;
    await audio.play();
  } catch (error) {
    console.error("Unable to play fart sound:", error);
  }
});
