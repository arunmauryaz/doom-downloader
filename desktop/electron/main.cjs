const { app, BrowserWindow, shell, dialog, ipcMain } = require("electron");
const path = require("path");
const { spawn, spawnSync } = require("child_process");
const fs = require("fs");
const http = require("http");

let mainWindow = null;
let pythonProcess = null;

const isDev = process.env.NODE_ENV === "development" || process.argv.includes("--dev");

function findProjectRoot() {
  const current = __dirname;
  // desktop/electron -> root is ..
  const rootCandidate = path.resolve(current, "../..");
  if (fs.existsSync(path.join(rootCandidate, "core", "engine.py"))) {
    return rootCandidate;
  }
  return process.cwd();
}

function findPython(projectRoot) {
  const venvWin = path.join(projectRoot, ".venv", "Scripts", "python.exe");
  if (fs.existsSync(venvWin)) return venvWin;
  const venvPosix = path.join(projectRoot, ".venv", "bin", "python");
  if (fs.existsSync(venvPosix)) return venvPosix;
  return process.platform === "win32" ? "python.exe" : "python3";
}

function startPythonBackend() {
  const projectRoot = findProjectRoot();
  const pythonBin = findPython(projectRoot);

  // Check if port 8080 is already active and responding
  const req = http.get("http://127.0.0.1:8080/api/status", (res) => {
    if (res.statusCode === 200) {
      console.log("[Desktop] Python engine server is already running on port 8080.");
    }
  });

  req.on("error", () => {
    // Port 8080 is not yet active, spawn python backend
    console.log(`[Desktop] Starting Python backend from: ${projectRoot}`);
    console.log(`[Desktop] Using Python: ${pythonBin}`);

    pythonProcess = spawn(
      pythonBin,
      ["main.py", "--server", "--host", "127.0.0.1", "--port", "8080"],
      {
        cwd: projectRoot,
        stdio: "pipe",
        windowsHide: true,
      }
    );

    pythonProcess.stdout.on("data", (data) => {
      const text = data.toString();
      if (text.includes("[Doom Server Ready]")) {
        console.log(`[Desktop Engine] ${text.trim()}`);
      }
    });

    pythonProcess.stderr.on("data", (data) => {
      console.error(`[Desktop Engine Err] ${data.toString()}`);
    });

    pythonProcess.on("close", (code) => {
      console.log(`[Desktop Engine] Exited with code ${code}`);
      pythonProcess = null;
    });
  });
}

function createWindow() {
  const iconPath = path.join(__dirname, "../assets/icon.ico");

  mainWindow = new BrowserWindow({
    width: 1120,
    height: 780,
    minWidth: 860,
    minHeight: 640,
    title: "Doom Downloader",
    backgroundColor: "#0e0e0e",
    autoHideMenuBar: true,
    show: false,
    icon: fs.existsSync(iconPath) ? iconPath : undefined,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: false,
      preload: path.join(__dirname, "preload.cjs"),
    },
  });

  // Handle external link clicks in system default browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith("http:") || url.startsWith("https:")) {
      shell.openExternal(url);
    }
    return { action: "deny" };
  });

  mainWindow.webContents.on("did-fail-load", (_event, errorCode, errorDescription) => {
    console.error(`[Desktop] Page failed to load: ${errorDescription} (${errorCode})`);
  });

  if (isDev) {
    mainWindow.loadURL("http://127.0.0.1:1420");
  } else {
    const distPath = path.join(__dirname, "../dist/index.html");
    if (fs.existsSync(distPath)) {
      mainWindow.loadFile(distPath);
    } else {
      mainWindow.loadURL("http://127.0.0.1:1420");
    }
  }

  mainWindow.once("ready-to-show", () => {
    if (mainWindow) {
      mainWindow.show();
      mainWindow.focus();
    }
  });

  // Safety fallback if ready-to-show event is missed
  setTimeout(() => {
    if (mainWindow && !mainWindow.isVisible()) {
      mainWindow.show();
      mainWindow.focus();
    }
  }, 1200);

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

// Single instance lock
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.show();
      mainWindow.focus();
    } else {
      createWindow();
    }
  });

  app.whenReady().then(() => {
    ipcMain.handle("dialog:selectFolder", async (_event, defaultPath) => {
      const result = await dialog.showOpenDialog(mainWindow, {
        properties: ["openDirectory", "createDirectory"],
        defaultPath: defaultPath || undefined,
        title: "Select Destination Folder",
      });
      if (!result.canceled && result.filePaths && result.filePaths.length > 0) {
        return result.filePaths[0];
      }
      return null;
    });

    ipcMain.handle("shell:revealFile", async (_event, filePath) => {
      if (filePath) {
        const resolved = path.resolve(filePath);
        if (fs.existsSync(resolved)) {
          shell.showItemInFolder(resolved);
          return true;
        }
      }
      return false;
    });

    ipcMain.handle("shell:openFile", async (_event, filePath) => {
      if (filePath) {
        const resolved = path.resolve(filePath);
        if (fs.existsSync(resolved)) {
          await shell.openPath(resolved);
          return true;
        }
      }
      return false;
    });

    startPythonBackend();
    createWindow();

    app.on("activate", () => {
      if (BrowserWindow.getAllWindows().length === 0) {
        createWindow();
      }
    });
  });

  app.on("will-quit", () => {
    if (pythonProcess && pythonProcess.pid) {
      try {
        if (process.platform === "win32") {
          spawnSync("taskkill", ["/pid", pythonProcess.pid.toString(), "/f", "/t"]);
        } else {
          pythonProcess.kill("SIGTERM");
        }
      } catch (e) {
        // ignore
      }
      pythonProcess = null;
    }
  });

  app.on("window-all-closed", () => {
    if (process.platform !== "darwin") {
      app.quit();
    }
  });
}
