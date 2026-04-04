import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("plugPffft", {
  onPlaySound: (callback: (audioUrl: string) => void) => {
    ipcRenderer.on("play-fart", (_event, audioUrl: string) => {
      callback(audioUrl);
    });
  }
});

declare global {
  interface Window {
    plugPffft: {
      onPlaySound: (callback: (audioUrl: string) => void) => void;
    };
  }
}
