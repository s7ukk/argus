const { app, BrowserWindow, ipcMain, shell, session, desktopCapturer, globalShortcut, screen } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');

app.commandLine.appendSwitch('autoplay-policy', 'no-user-gesture-required');
app.commandLine.appendSwitch('disable-background-timer-throttling');

const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
  app.quit();
  process.exit(0);
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });
}

let mainWindow = null;
let pythonProcess = null;
let logFilePath = null;

function getLogFile() {
  if (!logFilePath) {
    try {
      const uData = app.getPath('userData');
      fs.mkdirSync(uData, { recursive: true });
      logFilePath = path.join(uData, 'argus_runtime.log');
    } catch {}
  }
  return logFilePath;
}

function logApp(msg) {
  const line = `[${new Date().toISOString()}] ${msg}`;
  console.log(line);
  try {
    const f = getLogFile();
    if (f) fs.appendFileSync(f, line + '\n');
  } catch {}
}

function getFallbackScriptConfig() {
  const isWin = process.platform === 'win32';
  let pyCmd = isWin ? 'python' : 'python3';
  if (isWin) {
    const localApp = process.env.LOCALAPPDATA || '';
    const progFiles = process.env.ProgramFiles || 'C:\\Program Files';
    const pyCandidates = [
      path.join(localApp, 'Programs', 'Python', 'Python314', 'python.exe'),
      path.join(localApp, 'Programs', 'Python', 'Python312', 'python.exe'),
      path.join(localApp, 'Programs', 'Python', 'Python311', 'python.exe'),
      path.join(progFiles, 'Python314', 'python.exe'),
      path.join(progFiles, 'Python312', 'python.exe'),
    ];
    for (const p of pyCandidates) {
      if (fs.existsSync(p)) { pyCmd = p; break; }
    }
  } else {
    const macCandidates = [
      '/opt/homebrew/bin/python3',
      '/usr/local/bin/python3',
      '/Library/Frameworks/Python.framework/Versions/3.12/bin/python3',
      '/Library/Frameworks/Python.framework/Versions/3.11/bin/python3',
      '/usr/bin/python3'
    ];
    for (const p of macCandidates) {
      if (fs.existsSync(p)) { pyCmd = p; break; }
    }
  }

  const scriptCandidates = [
    process.resourcesPath ? path.join(process.resourcesPath, 'run_backend.py') : null,
    path.join(__dirname, '..', 'run_backend.py'),
    path.join(__dirname, '..', '..', 'run_backend.py'),
  ].filter(Boolean);

  let scriptPath = path.join(__dirname, '..', 'run_backend.py');
  let scriptCwd = path.join(__dirname, '..');
  for (const s of scriptCandidates) {
    if (fs.existsSync(s)) {
      scriptPath = s;
      scriptCwd = path.dirname(s);
      break;
    }
  }

  return { command: pyCmd, args: [scriptPath], cwd: scriptCwd, isBinary: false };
}

function getBackendConfig() {
  const isWin = process.platform === 'win32';
  const binaryName = isWin ? 'argus-backend.exe' : 'argus-backend';

  const safeCwd = app.isPackaged ? app.getPath('userData') : path.join(__dirname, '..');

  const candidates = [
    // 1. Packaged macOS Contents/MacOS/ location (standard for macOS helper binaries)
    process.resourcesPath ? path.join(process.resourcesPath, '..', 'MacOS', binaryName) : null,
    process.resourcesPath ? path.join(process.resourcesPath, '..', 'MacOS', 'argus-backend', binaryName) : null,
    // 2. Packaged location (resources/backend-dist/argus-backend/argus-backend)
    process.resourcesPath ? path.join(process.resourcesPath, 'backend-dist', 'argus-backend', binaryName) : null,
    process.resourcesPath ? path.join(process.resourcesPath, 'backend-dist', binaryName) : null,
    process.resourcesPath ? path.join(process.resourcesPath, binaryName) : null,
    // 3. Local dev repository location (backend-dist/argus-backend/argus-backend)
    path.join(__dirname, '..', 'backend-dist', 'argus-backend', binaryName),
    path.join(__dirname, '..', 'backend-dist', binaryName),
    path.join(__dirname, '..', '..', 'backend-dist', 'argus-backend', binaryName),
  ].filter(Boolean);

  for (const c of candidates) {
    if (fs.existsSync(c)) {
      logApp(`[Argus]: Found standalone backend binary at ${c}`);
      return { command: c, args: [], cwd: safeCwd, isBinary: true };
    }
  }

  const fb = getFallbackScriptConfig();
  fb.cwd = safeCwd;
  logApp(`[Argus]: Standalone binary not found, falling back to script: ${fb.command} ${fb.args.join(' ')}`);
  return fb;
}

function sanitizeLog(data) {
  let str = String(data);
  str = str.replace(/ARGUS-[A-Z0-9\-]+/gi, '[SECURED_KEY]');
  str = str.replace(/([?&])key_code=[^&\s]+/gi, '$1key_code=[SECURED]');
  str = str.replace(/postgres(?:ql)?:\/\/[^@\s]+@[^\s]+/gi, 'postgresql://[REDACTED_DB_CREDENTIALS]');
  str = str.replace(/fish-[a-zA-Z0-9_\-]+/gi, 'fish-[REDACTED]');
  str = str.replace(/Bearer\s+[a-zA-Z0-9_\-\.]+/gi, 'Bearer [REDACTED]');
  return str;
}

const LOCAL_HEALTH_URL = 'http://127.0.0.1:18274/api/health';
const CLOUD_HEALTH_URL = 'http://153.52.69.55:18274/api/health';

async function checkLocalBackendRunning() {
  try {
    const res = await fetch(LOCAL_HEALTH_URL, { signal: AbortSignal.timeout(2000) });
    return res.ok;
  } catch {
    return false;
  }
}

async function checkCloudServerRunning() {
  try {
    const res = await fetch(CLOUD_HEALTH_URL, { signal: AbortSignal.timeout(1500) });
    return res.ok;
  } catch {
    return false;
  }
}

async function checkBackendRunning() {
  return await checkLocalBackendRunning();
}

async function startPythonBackend() {
  const isLocalOk = await checkLocalBackendRunning();
  if (isLocalOk) {
    logApp('[Argus]: Python backend already running and healthy on port 18274.');
    return;
  }

  const isCloudOk = await checkCloudServerRunning();
  if (isCloudOk) {
    logApp('[Argus]: Central Cloud API verified online at http://153.52.69.55:18274.');
  }

  try {
    const cfg = getBackendConfig();
    logApp(`[Argus]: Spawning local backend: ${cfg.command} (args: ${JSON.stringify(cfg.args)})`);

    const isWin = process.platform === 'win32';
    const backendDir = process.resourcesPath ? path.join(process.resourcesPath, 'backend') : path.join(__dirname, '..', 'backend');
    const bDistDir = process.resourcesPath ? path.join(process.resourcesPath, 'backend-dist', 'argus-backend') : path.join(__dirname, '..', 'backend-dist', 'argus-backend');
    const internalDir = path.join(bDistDir, '_internal');

    const pyPath = [
      internalDir,
      bDistDir,
      backendDir,
      process.resourcesPath || path.join(__dirname, '..'),
      path.join(__dirname, '..')
    ].filter(p => p && fs.existsSync(p)).join(isWin ? ';' : ':');

    const macPaths = '/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin';
    const envPath = isWin ? (process.env.PATH || '') : `${macPaths}:${process.env.PATH || ''}`;

    const spawnEnv = Object.assign({}, process.env, {
      PYTHONUNBUFFERED: '1',
      PYTHONPATH: pyPath,
      PATH: envPath
    });

    if (process.platform === 'darwin') {
      try {
        const { execSync } = require('child_process');
        const bDir = process.resourcesPath
          ? path.join(process.resourcesPath, 'backend-dist')
          : path.join(__dirname, '..', 'backend-dist');
        if (fs.existsSync(bDir)) {
          try { execSync(`chmod -R 755 "${bDir}"`, { stdio: 'ignore' }); } catch {}
          try { execSync(`xattr -cr "${bDir}"`, { stdio: 'ignore' }); } catch {}
        }
        if (cfg.isBinary && fs.existsSync(cfg.command)) {
          try { fs.chmodSync(cfg.command, 0o755); } catch {}
          try { execSync(`xattr -cr "${cfg.command}"`, { stdio: 'ignore' }); } catch {}
        }
        // Also clear quarantine on app bundle if packaged
        if (process.resourcesPath) {
          try {
            const bundlePath = path.resolve(process.resourcesPath, '..', '..');
            if (bundlePath.endsWith('.app')) {
              execSync(`xattr -cr "${bundlePath}" 2>/dev/null || true`, { stdio: 'ignore' });
            }
          } catch {}
        }
      } catch (e) {
        logApp(`[Argus macOS prep notice]: ${e.message}`);
      }
    }

    pythonProcess = spawn(cfg.command, cfg.args, {
      cwd: cfg.cwd,
      env: spawnEnv,
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true
    });

    pythonProcess.on('error', (err) => {
      logApp(`[Argus backend error]: Failed to start backend process: ${err.message}`);
    });

    pythonProcess.stdout.on('data', (data) => {
      const sanitized = sanitizeLog(data);
      if (sanitized.trim()) logApp(`[Backend stdout]: ${sanitized.trim()}`);
    });

    pythonProcess.stderr.on('data', (data) => {
      const sanitized = sanitizeLog(data);
      if (sanitized.includes('10054') || sanitized.includes('_call_connection_lost')) return;
      if (sanitized.trim()) {
        logApp(`[Backend stderr]: ${sanitized.trim()}`);
        try {
          const uLog = path.join(app.getPath('userData'), 'backend_stderr.log');
          fs.appendFileSync(uLog, `[${new Date().toISOString()}] ${sanitized.trim()}
`);
        } catch {}
      }
    });

    pythonProcess.on('close', (code) => {
      logApp(`[Argus]: Backend process terminated (code: ${code})`);
      pythonProcess = null;
    });

    // Wait for backend to be fully active and healthy (up to 15 seconds)
    let isHealthy = false;
    for (let i = 0; i < 60; i++) {
      await new Promise(r => setTimeout(r, 250));
      if (await checkLocalBackendRunning()) {
        logApp('[Argus]: Python backend verified healthy on port 18274.');
        isHealthy = true;
        break;
      }
      // If process exited early with an error, don't keep waiting fruitlessly
      if (!pythonProcess && i >= 4) {
        logApp('[Argus]: Backend process exited prematurely.');
        break;
      }
    }

    // Dynamic Script Fallback if standalone binary fails or exits early
    if (!isHealthy && cfg.isBinary) {
      logApp('[Argus]: Standalone binary did not become healthy in time. Attempting fallback python script launch...');
      const fb = getFallbackScriptConfig();
      if (pythonProcess) {
        try { pythonProcess.kill(); } catch {}
      }
      logApp(`[Argus]: Spawning fallback script: ${fb.command} (args: ${JSON.stringify(fb.args)})`);
      pythonProcess = spawn(fb.command, fb.args, {
        cwd: fb.cwd,
        env: spawnEnv,
        stdio: ['ignore', 'pipe', 'pipe'],
        windowsHide: true
      });
      pythonProcess.stdout.on('data', (data) => {
        const s = sanitizeLog(data);
        if (s.trim()) logApp(`[Fallback stdout]: ${s.trim()}`);
      });
      pythonProcess.stderr.on('data', (data) => {
        const s = sanitizeLog(data);
        if (s.trim()) logApp(`[Fallback stderr]: ${s.trim()}`);
      });
      for (let i = 0; i < 40; i++) {
        await new Promise(r => setTimeout(r, 250));
        if (await checkLocalBackendRunning()) {
          logApp('[Argus]: Fallback Python backend verified healthy on port 18274.');
          break;
        }
      }
    }
  } catch (err) {
    logApp(`[Argus error]: Exception starting backend: ${err.message}`);
  }
}

const http = require('http');
let prodHttpServer = null;

function startProdHttpServer() {
  if (prodHttpServer) return;
  const distDir = path.join(__dirname, '..', 'dist');
  const mimeTypes = {
    '.html': 'text/html; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8',
    '.mjs': 'application/javascript; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.gif': 'image/gif',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon',
    '.webp': 'image/webp',
    '.woff2': 'font/woff2',
    '.woff': 'font/woff',
    '.ttf': 'font/ttf',
  };

  prodHttpServer = http.createServer((req, res) => {
    try {
      let reqPath = decodeURI(req.url.split('?')[0]);
      if (reqPath === '/' || !reqPath) reqPath = '/index.html';
      let target = path.join(distDir, reqPath);

      let isDir = false;
      try {
        if (fs.existsSync(target)) {
          isDir = fs.statSync(target).isDirectory();
        } else {
          target = path.join(distDir, 'index.html');
        }
      } catch {
        target = path.join(distDir, 'index.html');
      }

      if (isDir) {
        target = path.join(distDir, 'index.html');
      }

      const ext = path.extname(target).toLowerCase();
      const cType = mimeTypes[ext] || 'application/octet-stream';

      const data = fs.readFileSync(target);
      res.writeHead(200, {
        'Content-Type': cType,
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': '*',
        'Access-Control-Allow-Headers': '*',
        'Cache-Control': 'no-cache'
      });
      res.end(data);
    } catch {
      try {
        const fallback = fs.readFileSync(path.join(distDir, 'index.html'));
        res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
        res.end(fallback);
      } catch {
        res.writeHead(404);
        res.end('Not Found');
      }
    }
  });

  prodHttpServer.on('error', (err) => {
    logApp(`[Argus HTTP Server error]: ${err.message}`);
  });

  prodHttpServer.listen(18275, '127.0.0.1', () => {
    logApp('[Argus]: Production HTTP Loopback server active at http://127.0.0.1:18275');
  });
}

async function loadApp(window) {
  const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;
  const devUrl = 'http://127.0.0.1:5173';

  if (isDev) {
    try {
      const res = await fetch(devUrl, { signal: AbortSignal.timeout(500) });
      if (res.ok) {
        logApp('[Argus]: Connected to Vite dev server, loading URL...');
        await window.loadURL(devUrl);
        return;
      }
    } catch {}
  }

  // Production: serve over loopback HTTP server so cookies, localStorage, and CORS are 100% identical to dev mode!
  startProdHttpServer();
  let serverOk = false;
  for (let i = 0; i < 25; i++) {
    try {
      const r = await fetch('http://127.0.0.1:18275', { signal: AbortSignal.timeout(200) });
      if (r.ok) {
        serverOk = true;
        break;
      }
    } catch {}
    await new Promise(r => setTimeout(r, 80));
  }

  if (serverOk) {
    logApp('[Argus]: Loading production URL http://127.0.0.1:18275...');
    await window.loadURL('http://127.0.0.1:18275');
  } else {
    const fallbackPath = path.join(__dirname, '..', 'dist', 'index.html');
    logApp(`[Argus]: Loopback HTTP server not responding, falling back to loadFile: ${fallbackPath}`);
    await window.loadFile(fallbackPath);
  }
}

let ipcHandlersRegistered = false;

function registerIpcHandlers() {
  ipcMain.on('show-dictation-hud', () => {
    if (!dictationHudWindow || dictationHudWindow.isDestroyed()) createDictationHudWindow();
    if (dictationHudWindow) {
      try {
        const primaryDisplay = screen.getPrimaryDisplay();
        const { width } = primaryDisplay.workAreaSize;
        dictationHudWindow.setPosition(Math.round((width - 480) / 2), 35);
      } catch (e) {}
      dictationHudWindow.setAlwaysOnTop(true, 'screen-saver', 1);
      dictationHudWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
      dictationHudWindow.showInactive();
      dictationHudWindow.webContents.send('hud-update', { active: true });
    }
  });

  ipcMain.on('update-dictation-hud', (event, state) => {
    if (!dictationHudWindow || dictationHudWindow.isDestroyed()) return;
    dictationHudWindow.webContents.send('hud-update', state);
    if (state.success || state.error) {
      setTimeout(() => {
        try { dictationHudWindow?.hide(); } catch (e) {}
      }, 2000);
    }
  });

  ipcMain.on('hide-dictation-hud', () => {
    try { dictationHudWindow?.hide(); } catch (e) {}
  });

  if (ipcHandlersRegistered) return;
  ipcHandlersRegistered = true;

  ipcMain.on('window-minimize', () => {
    if (mainWindow) mainWindow.minimize();
  });

  ipcMain.on('window-maximize', () => {
    if (mainWindow) {
      if (mainWindow.isMaximized()) {
        mainWindow.unmaximize();
      } else {
        mainWindow.maximize();
      }
    }
  });

  ipcMain.on('window-close', () => {
    if (mainWindow) mainWindow.close();
  });

  ipcMain.on('open-external', (e, url) => {
    if (url && (url.startsWith('https://') || url.startsWith('http://'))) {
      shell.openExternal(url);
    }
  });

  try {
    ipcMain.removeHandler('take-desktop-screenshot');
  } catch {}

  ipcMain.handle('take-desktop-screenshot', async () => {
    try {
      const sources = await desktopCapturer.getSources({ types: ['screen'], thumbnailSize: { width: 1920, height: 1080 } });
      if (sources.length > 0) {
        const image = sources[0].thumbnail;
        const now = new Date();
        const pad = (n) => String(n).padStart(2, '0');
        const dateStr = `${now.getFullYear()}${pad(now.getMonth()+1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
        const desktopPath = path.join(app.getPath('desktop'), `screenshot_${dateStr}.png`);
        fs.writeFileSync(desktopPath, image.toPNG());
        return { success: true, path: desktopPath };
      }
    } catch (e) {
      logApp(`[Argus Screenshot error]: ${e.message}`);
    }
    return { success: false };
  });
}

let dictationHudWindow = null;

function createDictationHudWindow() {
  if (dictationHudWindow) return;
  const isMac = process.platform === 'darwin';
  
  dictationHudWindow = new BrowserWindow({
    width: 460,
    height: 60,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    skipTaskbar: true,
    focusable: false,
    resizable: false,
    show: false,
    hasShadow: false,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });

  dictationHudWindow.setAlwaysOnTop(true, 'screen-saver');
  dictationHudWindow.setVisibleOnAllWorkspaces(true);

  try {
    const primaryDisplay = screen.getPrimaryDisplay();
    const { width } = primaryDisplay.workAreaSize;
    dictationHudWindow.setPosition(Math.round((width - 460) / 2), 35);
  } catch (e) {}

  const html = `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      background: transparent;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100vh;
      user-select: none;
      overflow: hidden;
    }
    .hud-pill {
      background: rgba(15, 23, 42, 0.96);
      border: 1px solid rgba(168, 85, 247, 0.7);
      box-shadow: 0 16px 40px rgba(0, 0, 0, 0.7), 0 0 24px rgba(168, 85, 247, 0.35);
      border-radius: 30px;
      padding: 10px 22px;
      display: flex;
      align-items: center;
      gap: 12px;
      color: #ffffff;
      font-size: 13px;
      font-weight: 600;
      letter-spacing: 0.02em;
    }
    .dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: #ef4444;
      box-shadow: 0 0 10px #ef4444;
      animation: pulse 1.2s infinite ease-in-out;
    }
    @keyframes pulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.35; transform: scale(0.85); }
    }
  </style>
</head>
<body>
  <div class="hud-pill" id="pill">
    <div class="dot" id="dot"></div>
    <span id="text">🎙️ Голосовой ввод Argus: говорите текст... (Double-Ctrl)</span>
  </div>
  <script>
    const { ipcRenderer } = require('electron');
    ipcRenderer.on('hud-update', (event, state) => {
      const pill = document.getElementById('pill');
      const dot = document.getElementById('dot');
      const text = document.getElementById('text');
      if (state.active) {
        dot.style.background = '#ef4444';
        dot.style.boxShadow = '0 0 10px #ef4444';
        dot.style.display = 'block';
        pill.style.border = '1px solid rgba(168, 85, 247, 0.7)';
        text.innerText = '🎙️ Голосовой ввод Argus: говорите текст... (Double-Ctrl)';
      } else if (state.success) {
        dot.style.display = 'none';
        pill.style.border = '1px solid rgba(34, 197, 94, 0.8)';
        text.innerHTML = '<span style="color:#22c55e;font-size:15px;margin-right:4px;">✓</span> Вставлено: «' + (state.text || '') + '»';
      }
    });
  </script>
</body>
</html>`;

  dictationHudWindow.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(html)}`);
}

function createWindow() {
  const isMac = process.platform === 'darwin';
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 840,
    minWidth: 980,
    minHeight: 640,
    frame: false,
    titleBarStyle: isMac ? 'hiddenInset' : 'hidden',
    trafficLightPosition: isMac ? { x: 14, y: 11 } : undefined,
    backgroundColor: '#07050f',
    show: false, // Prevent white/blank flash before initial render
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      webSecurity: false,
      autoplayPolicy: 'no-user-gesture-required',
      backgroundThrottling: false
    }
  });

  session.defaultSession.setPermissionRequestHandler((webContents, permission, callback) => {
    callback(true);
  });

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  loadApp(mainWindow);

  // Pipe all frontend logs and errors directly to the persistent runtime log
  mainWindow.webContents.on('console-message', (event, level, message, line, sourceId) => {
    logApp(`[Frontend console (${level})]: ${message} (${sourceId}:${line})`);
  });

  mainWindow.webContents.on('render-process-gone', (event, details) => {
    logApp(`[Argus renderer crashed]: ${details.reason} (exitCode: ${details.exitCode})`);
  });

  mainWindow.webContents.on('before-input-event', (event, input) => {
    if (
      input.key === 'F12' ||
      ((input.control || input.meta) && input.shift && input.key.toLowerCase() === 'i')
    ) {
      mainWindow.webContents.toggleDevTools();
      event.preventDefault();
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(async () => {
  // Grant microphone and media access
  session.defaultSession.setPermissionRequestHandler((webContents, permission, callback) => {
    callback(true);
  });
  session.defaultSession.setPermissionCheckHandler((webContents, permission) => {
    return true;
  });

  if (process.platform === 'darwin') {
    const { systemPreferences } = require('electron');
    try {
      const micStatus = systemPreferences.getMediaAccessStatus('microphone');
      logApp(`[Argus]: macOS microphone status: ${micStatus}`);
      if (micStatus !== 'granted') {
        systemPreferences.askForMediaAccess('microphone').then((granted) => {
          logApp(`[Argus]: macOS microphone permission granted: ${granted}`);
        }).catch((err) => {
          logApp(`[Argus]: macOS microphone request error: ${err}`);
        });
      }
    } catch (e) {
      logApp(`[Argus mic permission exception]: ${e.message}`);
    }
  }

  registerIpcHandlers();
  await startPythonBackend();
  createWindow();
  createDictationHudWindow();

  // Background Long-Poller for Native Global Double-Ctrl Dictation
  let isDictationPollerActive = true;
  async function pollNativeDictation() {
    while (isDictationPollerActive) {
      try {
        const res = await fetch('http://127.0.0.1:18274/api/voice/dictation-poll');
        if (res.ok) {
          const data = await res.json();
          if (data.triggered && mainWindow) {
            mainWindow.webContents.send('voice-sunder-trigger');
          }
        } else {
          await new Promise((r) => setTimeout(r, 2000));
        }
      } catch {
        await new Promise((r) => setTimeout(r, 2000));
      }
    }
  }
  pollNativeDictation();

  // Register Voice Sunder Global Shortcut (Ctrl+Shift+V)
  try {
    globalShortcut.register('CommandOrControl+Shift+V', () => {
      if (mainWindow) {
        mainWindow.webContents.send('voice-sunder-trigger');
      }
    });
  } catch (e) {
    console.error('Failed to register global hotkey:', e);
  }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
  if (prodHttpServer) {
    try { prodHttpServer.close(); } catch {}
    prodHttpServer = null;
  }
  if (pythonProcess) {
    try {
      if (process.platform === 'win32' && pythonProcess.pid) {
        spawn('taskkill', ['/pid', String(pythonProcess.pid), '/f', '/t'], { stdio: 'ignore', windowsHide: true });
      } else {
        pythonProcess.kill('SIGTERM');
      }
    } catch {}
    pythonProcess = null;
  }
});
