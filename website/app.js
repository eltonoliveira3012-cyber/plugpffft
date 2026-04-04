const releaseStatus = document.getElementById("release-status");
const downloadCards = {
  macArm64: document.querySelector('[data-platform="macArm64"]'),
  macX64: document.querySelector('[data-platform="macX64"]'),
  windows: document.querySelector('[data-platform="windows"]')
};

function formatSize(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) {
    return "Installer ready";
  }

  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let unitIndex = 0;

  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }

  return `${value.toFixed(value >= 100 ? 0 : 1)} ${units[unitIndex]}`;
}

function setCardState(platform, payload) {
  const card = downloadCards[platform];
  if (!card) {
    return;
  }

  const meta = card.querySelector(".download-meta");

  if (!payload) {
    card.setAttribute("aria-disabled", "true");
    card.setAttribute("href", "#");
    meta.textContent = "Waiting for installer";
    return;
  }

  card.setAttribute("aria-disabled", "false");
  card.setAttribute("href", payload.url);
  meta.textContent = `${payload.filename} - ${formatSize(payload.sizeBytes)}`;
}

async function loadManifest() {
  try {
    const response = await fetch("./downloads/manifest.json", { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`Manifest returned ${response.status}`);
    }

    const manifest = await response.json();
    setCardState("macArm64", manifest.downloads?.macArm64 ?? manifest.downloads?.mac ?? null);
    setCardState("macX64", manifest.downloads?.macX64 ?? null);
    setCardState("windows", manifest.downloads?.windows);

    releaseStatus.textContent = `Version ${manifest.version} is live. Host this folder anywhere static files can be served.`;
  } catch (error) {
    setCardState("macArm64", null);
    setCardState("macX64", null);
    setCardState("windows", null);
    releaseStatus.textContent = "Upload installers with npm run site:bundle, then redeploy the website folder.";
    console.warn("Unable to load release manifest:", error);
  }
}

void loadManifest();
