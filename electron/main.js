const { app, BrowserWindow, ipcMain, shell, session, desktopCapturer, globalShortcut } = require('electron');
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

function getBackendConfig() {
  const isWin = process.platform === 'win32';
  const binaryName = isWin ? 'argus-backend.exe' : 'argus-backend';

  const candidates = [
    // 1. Packaged location (resources/backend-dist/argus-backend/argus-backend.exe)
    process.resourcesPath ? path.join(process.resourcesPath, 'backend-dist', 'argus-backend', binaryName) : null,
    process.resourcesPath ? path.join(process.resourcesPath, 'backend-dist', binaryName) : null,
    process.resourcesPath ? path.join(process.resourcesPath, binaryName) : null,
    // 2. Local dev repository location (backend-dist/argus-backend/argus-backend.exe)
    path.join(__dirname, '..', 'backend-dist', 'argus-backend', binaryName),
    path.join(__dirname, '..', 'backend-dist', binaryName),
    path.join(__dirname, '..', '..', 'backend-dist', 'argus-backend', binaryName),
  ].filter(Boolean);

  for (const c of candidates) {
    if (fs.existsSync(c)) {
      logApp(`[Argus]: Found standalone backend binary at ${c}`);
      return { command: c, args: [], cwd: path.dirname(c), isBinary: true };
    }
  }

  // 3. Fallback to system Python for developer mode or non-binary environment
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

  logApp(`[Argus]: Standalone binary not found, falling back to script: ${pyCmd} ${scriptPath}`);
  return { command: pyCmd, args: [scriptPath], cwd: scriptCwd, isBinary: false };
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

const CLOUD_HEALTH_URL = 'http://153.52.69.55:18274/api/health';

async function checkCloudServerRunning() {
  try {
    const res = await fetch(CLOUD_HEALTH_URL, { signal: AbortSignal.timeout(1500) });
    return res.ok;
  } catch {
    return false;
  }
}

async function checkBackendRunning() {
  return await checkCloudServerRunning();
}

async function startPythonBackend() {
  const isCloudOk = await checkCloudServerRunning();
  if (isCloudOk) {
    logApp('[Argus]: Central Cloud API verified online at http://153.52.69.55:18274.');
  }

  // On macOS, run purely in cloud client mode directly to central server
  if (process.platform === 'darwin') {
    logApp('[Argus]: macOS client mode active — connecting directly to central cloud server.');
    return;
  }

  try {
    const cfg = getBackendConfig();
    logApp(`[Argus]: Spawning local backend: ${cfg.command} (args: ${JSON.stringify(cfg.args)})`);

    if (process.platform !== 'win32' && cfg.isBinary) {
      try { fs.chmodSync(cfg.command, 0o755); } catch {}
    }

    pythonProcess = spawn(cfg.command, cfg.args, {
      cwd: cfg.cwd,
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
      if (sanitized.trim()) logApp(`[Backend stderr]: ${sanitized.trim()}`);
    });

    pythonProcess.on('close', (code) => {
      logApp(`[Argus]: Backend process terminated (code: ${code})`);
      pythonProcess = null;
    });

    // Wait for backend to be fully active and healthy
    for (let i = 0; i < 30; i++) {
      await new Promise(r => setTimeout(r, 300));
      if (await checkBackendRunning()) {
        logApp('[Argus]: Python backend verified healthy on port 18274.');
        break;
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
      autoplayPolicy: 'no-user-gesture-required'
    }
  });

  session.defaultSession.setPermissionRequestHandler((webContents, permission, callback) => {
    callback(true);
  });

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  loadApp(mainWindow);

  // Window IPC handlers
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
      console.error('Screenshot capture error:', e);
    }
    return { success: false };
  });

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

  await startPythonBackend();
  createWindow();

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
