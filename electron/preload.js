const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  minimize: () => ipcRenderer.send('window-minimize'),
  maximize: () => ipcRenderer.send('window-maximize'),
  close: () => ipcRenderer.send('window-close'),
  openExternal: (url) => ipcRenderer.send('open-external', url),
  takeScreenshot: () => ipcRenderer.invoke('take-desktop-screenshot'),
  onVoiceSunderTrigger: (cb) => ipcRenderer.on('voice-sunder-trigger', cb),
  showDictationHud: () => ipcRenderer.send('show-dictation-hud'),
  updateDictationHud: (state) => ipcRenderer.send('update-dictation-hud', state),
  hideDictationHud: () => ipcRenderer.send('hide-dictation-hud'),
  showIslandNotification: (data) => ipcRenderer.send('show-island-notification', data),
  hideIsland: () => ipcRenderer.send('hide-island'),
  isElectron: true,
  isMac: process.platform === 'darwin',
  platform: process.platform
});
