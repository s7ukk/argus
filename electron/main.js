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

function loadDotEnvFiles() {
  const envCandidates = [
    process.resourcesPath ? path.join(process.resourcesPath, '.env') : null,
    path.join(__dirname, '..', '.env'),
    path.join(__dirname, '..', '..', '.env'),
    app.isPackaged ? path.join(app.getPath('userData'), '.env') : null,
  ].filter(Boolean);

  const loadedVars = {};
  for (const envFile of envCandidates) {
    if (fs.existsSync(envFile)) {
      try {
        const content = fs.readFileSync(envFile, 'utf-8');
        for (const line of content.split('\n')) {
          const trimmed = line.trim();
          if (trimmed && !trimmed.startsWith('#') && trimmed.includes('=')) {
            const idx = trimmed.indexOf('=');
            const k = trimmed.substring(0, idx).trim();
            const v = trimmed.substring(idx + 1).trim().replace(/^['"]|['"]$/g, '');
            if (k && v && v !== 'your_openrouter_api_key_here') {
              process.env[k] = v;
              loadedVars[k] = v;
            }
          }
        }
      } catch {}
    }
  }
  return loadedVars;
}

async function startPythonBackend() {
  const dotEnvVars = loadDotEnvFiles();
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

    const spawnEnv = Object.assign({}, process.env, dotEnvVars, {
      PYTHONUNBUFFERED: '1',
      PYTHONPATH: pyPath,
      PATH: envPath,
      ARGUS_RESOURCES_PATH: process.resourcesPath || ''
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
        dictationHudWindow.setPosition(Math.round((width - 520) / 2), 12);
      } catch (e) {}
      // Temporarily bring on top during active Double-Ctrl dictation
      dictationHudWindow.setAlwaysOnTop(true, 'screen-saver', 1);
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
    try {
      dictationHudWindow?.setAlwaysOnTop(false);
      dictationHudWindow?.hide();
    } catch (e) {}
  });

  ipcMain.on('hud-mouse-state', (event, hovered) => {
    if (dictationHudWindow && !dictationHudWindow.isDestroyed()) {
      if (hovered) {
        dictationHudWindow.setIgnoreMouseEvents(false);
      } else {
        dictationHudWindow.setIgnoreMouseEvents(true, { forward: true });
      }
    }
  });

  ipcMain.on('show-island-notification', (event, data) => {
    if (!dictationHudWindow || dictationHudWindow.isDestroyed()) createDictationHudWindow();
    if (dictationHudWindow) {
      try {
        const primaryDisplay = screen.getPrimaryDisplay();
        const { width } = primaryDisplay.workAreaSize;
        dictationHudWindow.setPosition(Math.round((width - 520) / 2), 12);
      } catch (e) {}
      dictationHudWindow.setAlwaysOnTop(false);
      dictationHudWindow.showInactive();
      dictationHudWindow.webContents.send('island-notify', data);
    }
  });

  ipcMain.on('hide-island', () => {
    try { dictationHudWindow?.hide(); } catch (e) {}
  });

  ipcMain.on('update-island-timer', (event, timer) => {
    if (!dictationHudWindow || dictationHudWindow.isDestroyed()) createDictationHudWindow();
    if (dictationHudWindow) {
      if (timer && timer.is_running && timer.remaining_seconds > 0) {
        try {
          const primaryDisplay = screen.getPrimaryDisplay();
          const { width } = primaryDisplay.workAreaSize;
          dictationHudWindow.setPosition(Math.round((width - 520) / 2), 12);
        } catch (e) {}
        dictationHudWindow.setAlwaysOnTop(false);
        dictationHudWindow.showInactive();
        dictationHudWindow.webContents.send('island-timer', timer);
      } else {
        dictationHudWindow.webContents.send('island-timer', null);
      }
    }
  });

  ipcMain.on('update-island-state', (event, state) => {
    if (!dictationHudWindow || dictationHudWindow.isDestroyed()) createDictationHudWindow();
    if (dictationHudWindow) {
      if (state.thinking || state.speaking) {
        try {
          const primaryDisplay = screen.getPrimaryDisplay();
          const { width } = primaryDisplay.workAreaSize;
          dictationHudWindow.setPosition(Math.round((width - 520) / 2), 12);
        } catch (e) {}
        dictationHudWindow.setAlwaysOnTop(false);
        dictationHudWindow.showInactive();
        dictationHudWindow.webContents.send('island-state', state);
      } else if (state.idle) {
        dictationHudWindow.webContents.send('island-state', { idle: true });
      }
    }
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
    width: 520,
    height: 220,
    frame: false,
    transparent: true,
    alwaysOnTop: false, // Desktop level by default - does NOT block other applications
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

  dictationHudWindow.setAlwaysOnTop(false);
  dictationHudWindow.setIgnoreMouseEvents(true, { forward: true });

  try {
    const primaryDisplay = screen.getPrimaryDisplay();
    const { width } = primaryDisplay.workAreaSize;
    dictationHudWindow.setPosition(Math.round((width - 520) / 2), 12);
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
      justify-content: center;
      align-items: flex-start;
      height: 100vh;
      user-select: none;
      overflow: hidden;
      padding-top: 6px;
      pointer-events: none;
    }

    .hud-pill {
      pointer-events: auto;
      cursor: default;
      background: rgba(13, 13, 18, 0.94);
      backdrop-filter: blur(28px);
      -webkit-backdrop-filter: blur(28px);
      border: 1px solid rgba(255, 255, 255, 0.14);
      box-shadow: 0 16px 36px rgba(0, 0, 0, 0.72), 0 0 1px rgba(255, 255, 255, 0.25);
      border-radius: 9999px;
      padding: 7px 18px;
      display: flex;
      flex-direction: column;
      align-items: center;
      color: #ffffff;
      font-size: 13px;
      font-weight: 600;
      letter-spacing: 0.02em;
      transition: all 0.28s cubic-bezier(0.16, 1, 0.3, 1);
      width: auto;
      min-width: 140px;
      max-width: 480px;
    }

    /* Hover expanded state */
    .hud-pill:hover, .hud-pill.is-expanded {
      border-radius: 20px;
      padding: 14px 20px;
      width: 460px;
      max-width: 460px;
      background: rgba(15, 15, 22, 0.97);
      border-color: rgba(255, 255, 255, 0.24);
      box-shadow: 0 24px 50px rgba(0, 0, 0, 0.85), 0 0 1px rgba(255, 255, 255, 0.3);
    }

    .pill-header {
      display: flex;
      align-items: center;
      gap: 10px;
      width: 100%;
      justify-content: center;
    }

    .hud-pill:hover .pill-header, .hud-pill.is-expanded .pill-header {
      justify-content: space-between;
    }

    .online-dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: #4ade80;
      box-shadow: 0 0 8px #4ade80;
      flex-shrink: 0;
    }

    .dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #ef4444;
      box-shadow: 0 0 10px #ef4444;
      animation: pulse 1.2s infinite ease-in-out;
      flex-shrink: 0;
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.35; transform: scale(0.85); }
    }

    @keyframes dotRun1 {
      0% { transform: translateX(0); }
      33% { transform: translateX(7px); }
      66% { transform: translateX(14px); }
      100% { transform: translateX(0); }
    }
    @keyframes dotRun2 {
      0% { transform: translateX(0); }
      33% { transform: translateX(7px); }
      66% { transform: translateX(-7px); }
      100% { transform: translateX(0); }
    }
    @keyframes dotRun3 {
      0% { transform: translateX(0); }
      33% { transform: translateX(-14px); }
      66% { transform: translateX(-7px); }
      100% { transform: translateX(0); }
    }
    .anim-dot-run-1 { animation: dotRun1 1.4s infinite cubic-bezier(0.4, 0, 0.2, 1); }
    .anim-dot-run-2 { animation: dotRun2 1.4s infinite cubic-bezier(0.4, 0, 0.2, 1); }
    .anim-dot-run-3 { animation: dotRun3 1.4s infinite cubic-bezier(0.4, 0, 0.2, 1); }

    @keyframes soundwave {
      0%, 100% { height: 4px; }
      50% { height: 15px; }
    }
    .wave-bar {
      width: 2.5px;
      background: #ffffff;
      border-radius: 2px;
      display: inline-block;
      animation: soundwave 0.8s ease-in-out infinite;
    }

    /* Expandable Body */
    .expanded-body {
      max-height: 0;
      opacity: 0;
      overflow: hidden;
      width: 100%;
      transition: max-height 0.28s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.22s ease, margin-top 0.22s ease;
      margin-top: 0;
      pointer-events: none;
    }

    .hud-pill:hover .expanded-body, .hud-pill.is-expanded .expanded-body {
      max-height: 150px;
      opacity: 1;
      margin-top: 12px;
      pointer-events: auto;
    }

    .divider {
      height: 1px;
      background: rgba(255, 255, 255, 0.09);
      width: 100%;
      margin-bottom: 10px;
    }

    .details-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 8px;
    }

    .timer-large {
      font-size: 24px;
      font-weight: 800;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      color: #ffffff;
      letter-spacing: 0.05em;
    }

    .sub-hint {
      font-size: 11px;
      color: #94a3b8;
      font-weight: 500;
      line-height: 1.45;
    }

    .badge-tag {
      font-size: 10px;
      padding: 2px 7px;
      border-radius: 6px;
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.1);
      color: #cbd5e1;
      font-weight: 600;
      letter-spacing: 0.03em;
    }
  </style>
</head>
<body>
  <div class="hud-pill" id="pill">
    <div class="pill-header">
      <div style="display:flex;align-items:center;gap:8px;">
        <div class="online-dot" id="online-dot"></div>
        <div class="dot" id="dot" style="display:none;"></div>
        <div id="thinking-dots" style="display:none;align-items:center;gap:3px;margin-right:2px;">
          <span class="anim-dot-run-1" style="width:4.5px;height:4.5px;border-radius:50%;background:#ffffff;display:inline-block;"></span>
          <span class="anim-dot-run-2" style="width:4.5px;height:4.5px;border-radius:50%;background:#ffffff;opacity:0.8;display:inline-block;"></span>
          <span class="anim-dot-run-3" style="width:4.5px;height:4.5px;border-radius:50%;background:#ffffff;opacity:0.6;display:inline-block;"></span>
        </div>
        <div id="soundwave" style="display:none;align-items:center;gap:2.5px;margin-right:4px;">
          <span class="wave-bar" style="height:6px;animation-delay:0s;"></span>
          <span class="wave-bar" style="height:14px;animation-delay:0.18s;"></span>
          <span class="wave-bar" style="height:10px;animation-delay:0.36s;"></span>
        </div>
        <div id="icon" style="display:none;align-items:center;"></div>
        <span id="text" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">Argus AI</span>
      </div>
      <span class="badge-tag" id="header-tag" style="display:none;">OS</span>
    </div>

    <!-- Expanded content on Hover -->
    <div class="expanded-body" id="expanded-body">
      <div class="divider"></div>
      
      <!-- Timer details if active -->
      <div id="expanded-timer-section" style="display:none;margin-bottom:8px;">
        <div style="display:flex;align-items:baseline;justify-content:space-between;">
          <span id="exp-timer-title" style="font-size:12px;color:#cbd5e1;font-weight:600;">Активный таймер</span>
          <span class="timer-large" id="exp-timer-digits">00:00</span>
        </div>
        <div style="font-size:11px;color:#fbbf24;margin-top:2px;display:flex;align-items:center;gap:5px;">
          <span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:#fbbf24;"></span>
          Отсчет времени в процессе
        </div>
      </div>

      <!-- General status & hint -->
      <div id="expanded-info-section">
        <div class="details-row">
          <span style="font-size:11.5px;color:#cbd5e1;font-weight:600;">Argus AI Butler</span>
          <span class="badge-tag">На связи • Готов</span>
        </div>
        <div class="sub-hint" id="exp-hint">
          ⌨️ Двойной Ctrl: голосовой ввод в любую программу<br>
          ⚡ Без задержек • Монохромный дизайн
        </div>
      </div>
    </div>
  </div>
  <script>
    const { ipcRenderer } = require('electron');
    let hideTimeout = null;
    let isThinking = false;
    let isSpeaking = false;
    let isDictating = false;
    let activeTimer = null;

    const pill = document.getElementById('pill');
    pill.addEventListener('mouseenter', () => {
      try { ipcRenderer.send('hud-mouse-state', true); } catch (e) {}
    });
    pill.addEventListener('mouseleave', () => {
      try { ipcRenderer.send('hud-mouse-state', false); } catch (e) {}
    });

    const ICONS = {
      check: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#4ade80" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>',
      alert: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
      timer: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fbbf24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
      info: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>'
    };

    function formatTime(totalSec) {
      const m = Math.floor(totalSec / 60);
      const s = totalSec % 60;
      return (m < 10 ? '0' : '') + m + ':' + (s < 10 ? '0' : '') + s;
    }

    function renderActiveState() {
      if (hideTimeout) clearTimeout(hideTimeout);
      const onlineDot = document.getElementById('online-dot');
      const dot = document.getElementById('dot');
      const tDots = document.getElementById('thinking-dots');
      const wave = document.getElementById('soundwave');
      const icon = document.getElementById('icon');
      const text = document.getElementById('text');
      const headerTag = document.getElementById('header-tag');
      const expTimerSec = document.getElementById('expanded-timer-section');
      const expTimerTitle = document.getElementById('exp-timer-title');
      const expTimerDigits = document.getElementById('exp-timer-digits');
      const expHint = document.getElementById('exp-hint');

      if (isDictating) return;

      if (isThinking) {
        onlineDot.style.display = 'none';
        dot.style.display = 'none';
        icon.style.display = 'none';
        wave.style.display = 'none';
        tDots.style.display = 'flex';
        pill.style.borderColor = 'rgba(255, 255, 255, 0.25)';
        text.innerText = 'Thinking...';
        headerTag.style.display = 'block';
        headerTag.innerText = 'AI';
        expTimerSec.style.display = 'none';
        expHint.innerText = 'Нейросеть обрабатывает запрос и генерирует структурированный ответ...';
        return;
      }

      if (isSpeaking) {
        onlineDot.style.display = 'none';
        dot.style.display = 'none';
        icon.style.display = 'none';
        tDots.style.display = 'none';
        wave.style.display = 'flex';
        pill.style.borderColor = 'rgba(255, 255, 255, 0.25)';
        text.innerText = 'Озвучивание...';
        headerTag.style.display = 'block';
        headerTag.innerText = 'TTS';
        expTimerSec.style.display = 'none';
        expHint.innerText = 'Голосовой синтез (Дмитрий) озвучивает ответ с чистым звучанием.';
        return;
      }

      if (activeTimer && activeTimer.is_running && activeTimer.remaining_seconds > 0) {
        onlineDot.style.display = 'none';
        dot.style.display = 'none';
        tDots.style.display = 'none';
        wave.style.display = 'none';
        icon.style.display = 'flex';
        icon.innerHTML = ICONS.timer;
        pill.style.borderColor = 'rgba(251, 191, 36, 0.45)';
        text.innerHTML = '<span style="color:#e2e8f0;margin-right:6px;">' + (activeTimer.title || 'Таймер') + '</span><span style="color:#ffffff;font-weight:800;font-family:monospace;letter-spacing:0.04em;">' + formatTime(activeTimer.remaining_seconds) + '</span>';
        headerTag.style.display = 'none';
        expTimerSec.style.display = 'block';
        expTimerTitle.innerText = activeTimer.title || 'Таймер';
        expTimerDigits.innerText = formatTime(activeTimer.remaining_seconds);
        expHint.innerText = 'Отсчет времени выполняется в фоновом режиме Argus.';
        return;
      }

      // Standby / Idle on Desktop
      onlineDot.style.display = 'block';
      dot.style.display = 'none';
      tDots.style.display = 'none';
      wave.style.display = 'none';
      icon.style.display = 'none';
      headerTag.style.display = 'none';
      pill.style.borderColor = 'rgba(255, 255, 255, 0.12)';
      text.innerText = 'Argus AI';
      expTimerSec.style.display = 'none';
      expHint.innerHTML = '⌨️ Двойной Ctrl: голосовой ввод в любую программу<br>⚡ Все системы работают в штатном режиме';
    }

    ipcRenderer.on('island-timer', (event, timer) => {
      activeTimer = timer;
      renderActiveState();
    });

    ipcRenderer.on('hud-update', (event, state) => {
      if (hideTimeout) clearTimeout(hideTimeout);
      const onlineDot = document.getElementById('online-dot');
      const dot = document.getElementById('dot');
      const tDots = document.getElementById('thinking-dots');
      const wave = document.getElementById('soundwave');
      const icon = document.getElementById('icon');
      const text = document.getElementById('text');
      const headerTag = document.getElementById('header-tag');
      const expTimerSec = document.getElementById('expanded-timer-section');
      const expHint = document.getElementById('exp-hint');

      onlineDot.style.display = 'none';
      tDots.style.display = 'none';
      wave.style.display = 'none';
      expTimerSec.style.display = 'none';

      if (state.active) {
        isDictating = true;
        dot.style.display = 'block';
        dot.style.background = '#ef4444';
        dot.style.boxShadow = '0 0 10px #ef4444';
        icon.style.display = 'none';
        headerTag.style.display = 'block';
        headerTag.innerText = 'REC';
        pill.style.borderColor = 'rgba(239, 68, 68, 0.6)';
        text.innerText = 'Голосовой ввод Argus... (Double-Ctrl)';
        expHint.innerText = 'Идет запись речи с микрофона. Нажмите Double-Ctrl для вставки текста.';
      } else if (state.success) {
        isDictating = false;
        dot.style.display = 'none';
        icon.style.display = 'flex';
        icon.innerHTML = ICONS.check;
        headerTag.style.display = 'none';
        pill.style.borderColor = 'rgba(74, 222, 128, 0.5)';
        text.innerText = 'Вставлено: «' + (state.text || '') + '»';
        expHint.innerText = 'Текст успешно введен в активное окно приложения.';
        setTimeout(renderActiveState, 1800);
      }
    });

    ipcRenderer.on('island-notify', (event, data) => {
      if (hideTimeout) clearTimeout(hideTimeout);
      const onlineDot = document.getElementById('online-dot');
      const dot = document.getElementById('dot');
      const tDots = document.getElementById('thinking-dots');
      const wave = document.getElementById('soundwave');
      const icon = document.getElementById('icon');
      const text = document.getElementById('text');

      onlineDot.style.display = 'none';
      dot.style.display = 'none';
      tDots.style.display = 'none';
      wave.style.display = 'none';
      icon.style.display = 'flex';

      if (data.type === 'success') {
        icon.innerHTML = ICONS.check;
        pill.style.borderColor = 'rgba(74, 222, 128, 0.5)';
      } else if (data.type === 'alert') {
        icon.innerHTML = ICONS.alert;
        pill.style.borderColor = 'rgba(239, 68, 68, 0.5)';
      } else if (data.type === 'timer') {
        icon.innerHTML = ICONS.timer;
        pill.style.borderColor = 'rgba(251, 191, 36, 0.5)';
      } else {
        icon.innerHTML = ICONS.info;
        pill.style.borderColor = 'rgba(255, 255, 255, 0.2)';
      }

      text.innerText = data.text || '';

      hideTimeout = setTimeout(() => {
        renderActiveState();
      }, data.duration || 2800);
    });

    ipcRenderer.on('island-state', (event, state) => {
      if (state.thinking) {
        isThinking = true;
        isSpeaking = false;
      } else if (state.speaking) {
        isSpeaking = true;
        isThinking = false;
      } else if (state.idle) {
        isThinking = false;
        isSpeaking = false;
      }
      renderActiveState();
    });

    // Initial render
    renderActiveState();
  </script>
</body>
</html>`;

  dictationHudWindow.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(html)}`);
  dictationHudWindow.showInactive();
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
    // Protect Argus AI from closing when Ctrl+W / Cmd+W is received
    if (
      (input.control || input.meta) &&
      !input.alt &&
      input.key.toLowerCase() === 'w'
    ) {
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
