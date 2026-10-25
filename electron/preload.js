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
  updateIslandState: (state) => ipcRenderer.send('update-island-state', state),
  updateIslandTimer: (timer) => ipcRenderer.send('update-island-timer', timer),
  onStopActiveTimer: (cb) => ipcRenderer.on('stop-active-timer', cb),
  onCancelAiAction: (cb) => ipcRenderer.on('cancel-ai-action', cb),
  stopActiveTimer: () => ipcRenderer.send('stop-active-timer'),
  cancelAiAction: () => ipcRenderer.send('cancel-ai-action'),
  isElectron: true,
  isMac: process.platform === 'darwin',
  platform: process.platform
});
