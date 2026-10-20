const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  minimize: () => ipcRenderer.send('window-minimize'),
  maximize: () => ipcRenderer.send('window-maximize'),
  close: () => ipcRenderer.send('window-close'),
  openExternal: (url) => ipcRenderer.send('open-external', url),
  takeScreenshot: () => ipcRenderer.invoke('take-desktop-screenshot'),
  onVoiceSunderTrigger: (cb) => ipcRenderer.on('voice-sunder-trigger', cb),
  isElectron: true,
  isMac: process.platform === 'darwin',
  platform: process.platform
});
