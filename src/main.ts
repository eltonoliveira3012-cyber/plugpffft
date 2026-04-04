import { app, BrowserWindow, Menu, MenuItemConstructorOptions, MenuItem, Tray, nativeImage, powerMonitor, shell } from "electron";
import { execSync } from "node:child_process";
import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

type PowerState = "ac" | "battery" | "unknown";
type SoundKind = "connect" | "disconnect";

type Settings = {
  playOnConnect: boolean;
  playOnDisconnect: boolean;
  launchAtLogin: boolean;
};

const PRODUCT_NAME = "PlugPffft";
const DEFAULT_SETTINGS: Settings = {
  playOnConnect: true,
  playOnDisconnect: true,
  launchAtLogin: true
};

let tray: Tray | null = null;
let playerWindow: BrowserWindow | null = null;
let settings: Settings = { ...DEFAULT_SETTINGS };
let powerState: PowerState = "unknown";

const singleInstanceLock = app.requestSingleInstanceLock();
if (!singleInstanceLock) {
  app.quit();
}

app.commandLine.appendSwitch("autoplay-policy", "no-user-gesture-required");
app.setName(PRODUCT_NAME);
app.on("second-instance", () => {
  tray?.popUpContextMenu();
});

function getSettingsPath(): string {
  return path.join(app.getPath("userData"), "settings.json");
}

function resolveExtraAsset(...segments: string[]): string {
  const assetRoot = app.isPackaged ? path.join(process.resourcesPath, "assets") : path.join(app.getAppPath(), "assets");
  return path.join(assetRoot, ...segments);
}

function resolveDistFile(...segments: string[]): string {
  return path.join(__dirname, ...segments);
}

async function loadSettings(): Promise<void> {
  const filePath = getSettingsPath();

  try {
    const raw = await fs.readFile(filePath, "utf8");
    const parsed = JSON.parse(raw) as Partial<Settings>;
    settings = {
      ...DEFAULT_SETTINGS,
      ...parsed
    };
  } catch {
    settings = { ...DEFAULT_SETTINGS };
    await saveSettings();
  }
}

async function saveSettings(): Promise<void> {
  const filePath = getSettingsPath();
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  await fs.writeFile(filePath, `${JSON.stringify(settings, null, 2)}\n`, "utf8");
}

function applyLaunchAtLogin(): void {
  app.setLoginItemSettings({
    openAtLogin: settings.launchAtLogin,
    openAsHidden: true
  });
}

function getTrayImage() {
  const iconPath = process.platform === "darwin"
    ? resolveExtraAsset("app", "trayTemplate.png")
    : resolveExtraAsset("app", "tray.png");
  const icon = nativeImage.createFromPath(iconPath);

  if (icon.isEmpty()) {
    throw new Error(`Tray icon missing at ${iconPath}`);
  }

  if (process.platform === "darwin") {
    icon.setTemplateImage(true);
  }

  return icon;
}

function getPowerStatusLabel(): string {
  if (powerState === "ac") {
    return "Plugged in";
  }

  if (powerState === "battery") {
    return "On battery";
  }

  return "Unavailable";
}

function refreshTrayMenu(): void {
  if (!tray) {
    return;
  }

  const menuTemplate: MenuItemConstructorOptions[] = [
    { label: PRODUCT_NAME, enabled: false },
    { type: "separator" },
    { label: `Power: ${getPowerStatusLabel()}`, enabled: false },
    {
      label: "Test plug-in fart",
      click: () => {
        void playFart("connect");
      }
    },
    {
      label: "Test unplug fart",
      click: () => {
        void playFart("disconnect");
      }
    },
    {
      label: "Play when charger connects",
      type: "checkbox",
      checked: settings.playOnConnect,
      click: (menuItem: MenuItem) => {
        settings.playOnConnect = menuItem.checked;
        void saveSettings();
        refreshTrayMenu();
      }
    },
    {
      label: "Play when charger disconnects",
      type: "checkbox",
      checked: settings.playOnDisconnect,
      click: (menuItem: MenuItem) => {
        settings.playOnDisconnect = menuItem.checked;
        void saveSettings();
        refreshTrayMenu();
      }
    },
    {
      label: "Launch at login",
      type: "checkbox",
      checked: settings.launchAtLogin,
      click: (menuItem: MenuItem) => {
        settings.launchAtLogin = menuItem.checked;
        applyLaunchAtLogin();
        void saveSettings();
        refreshTrayMenu();
      }
    },
    { type: "separator" },
    {
      label: `Open ${PRODUCT_NAME} data folder`,
      click: () => {
        shell.showItemInFolder(app.getPath("userData"));
      }
    },
    {
      label: `Quit ${PRODUCT_NAME}`,
      click: () => {
        app.quit();
      }
    }
  ];

  tray.setContextMenu(Menu.buildFromTemplate(menuTemplate));
  tray.setToolTip(`${PRODUCT_NAME} - ${getPowerStatusLabel()}`);
}

async function createPlayerWindow(): Promise<void> {
  if (playerWindow && !playerWindow.isDestroyed()) {
    return;
  }

  playerWindow = new BrowserWindow({
    show: false,
    width: 320,
    height: 180,
    frame: false,
    transparent: true,
    resizable: false,
    movable: false,
    skipTaskbar: true,
    webPreferences: {
      backgroundThrottling: false,
      contextIsolation: true,
      preload: resolveDistFile("preload.js"),
      sandbox: false
    }
  });

  playerWindow.on("closed", () => {
    playerWindow = null;
  });

  await playerWindow.loadFile(resolveDistFile("player", "player.html"));
}

async function playFart(kind: SoundKind): Promise<void> {
  await createPlayerWindow();

  const fartSoundFile = kind === "connect" ? "plugged-fart.mp3" : "unplugged-fart.mp3";
  const fartSoundPath = resolveExtraAsset("audio", fartSoundFile);
  const fartSoundUrl = pathToFileURL(fartSoundPath).toString();
  playerWindow?.webContents.send("play-fart", fartSoundUrl);
}

function setPowerState(nextState: PowerState): void {
  powerState = nextState;
  refreshTrayMenu();
}

function currentPowerState(): PowerState {
  try {
    return powerMonitor.isOnBatteryPower() ? "battery" : "ac";
  } catch {
    return "unknown";
  }
}

function wirePowerEvents(): void {
  setPowerState(currentPowerState());

  powerMonitor.on("on-battery", () => {
    const previous = powerState;
    setPowerState("battery");

    if (previous !== "battery" && settings.playOnDisconnect) {
      void playFart("disconnect");
    }
  });

  powerMonitor.on("on-ac", () => {
    const previous = powerState;
    setPowerState("ac");

    if (previous !== "ac" && settings.playOnConnect) {
      void playFart("connect");
    }
  });
}

// ---------------------------------------------------------------------------
// Suppress the native OS charging sound so only the fart plays
// ---------------------------------------------------------------------------

function suppressNativeChargingSound(): void {
  try {
    if (process.platform === "darwin") {
      execSync("defaults write com.apple.PowerChime ChimeOnAllHardware -bool false");
      execSync("killall PowerChime 2>/dev/null || true");
    } else if (process.platform === "win32") {
      execSync('reg add "HKCU\\AppEvents\\Schemes\\Apps\\.Default\\DeviceConnect\\.Current" /ve /t REG_SZ /d "" /f');
      execSync('reg add "HKCU\\AppEvents\\Schemes\\Apps\\.Default\\DeviceDisconnect\\.Current" /ve /t REG_SZ /d "" /f');
    }
  } catch {
    // Best-effort — not critical if it fails
  }
}

function restoreNativeChargingSound(): void {
  try {
    if (process.platform === "darwin") {
      execSync("defaults write com.apple.PowerChime ChimeOnAllHardware -bool true");
    } else if (process.platform === "win32") {
      execSync('reg add "HKCU\\AppEvents\\Schemes\\Apps\\.Default\\DeviceConnect\\.Current" /ve /t REG_SZ /d "C:\\Windows\\Media\\Windows Hardware Insert.wav" /f');
      execSync('reg add "HKCU\\AppEvents\\Schemes\\Apps\\.Default\\DeviceDisconnect\\.Current" /ve /t REG_SZ /d "C:\\Windows\\Media\\Windows Hardware Remove.wav" /f');
    }
  } catch {
    // Best-effort
  }
}

function createTray(): void {
  tray = new Tray(getTrayImage());
  tray.setIgnoreDoubleClickEvents(true);
  refreshTrayMenu();
  tray.on("click", () => {
    tray?.popUpContextMenu();
  });
}

async function bootstrap(): Promise<void> {
  await app.whenReady();

  if (process.platform === "darwin") {
    app.dock.hide();
  }

  await loadSettings();
  applyLaunchAtLogin();
  suppressNativeChargingSound();
  await createPlayerWindow();
  createTray();
  wirePowerEvents();

  app.on("activate", () => {
    tray?.popUpContextMenu();
  });

  app.on("will-quit", () => {
    restoreNativeChargingSound();
  });
}

void bootstrap().catch((error) => {
  console.error("PlugPffft failed to start:", error);
  app.quit();
});
