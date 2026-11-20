const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("electronAPI", {
  isElectron: true,
  selectFolder: (defaultPath) => ipcRenderer.invoke("dialog:selectFolder", defaultPath),
  revealFile: (filePath) => ipcRenderer.invoke("shell:revealFile", filePath),
  openFile: (filePath) => ipcRenderer.invoke("shell:openFile", filePath),
});
