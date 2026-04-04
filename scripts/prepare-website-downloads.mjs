import { copyFile, mkdir, readFile, readdir, rm, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const rootDir = path.dirname(fileURLToPath(import.meta.url));
const projectDir = path.resolve(rootDir, "..");
const releaseDir = path.join(projectDir, "release");
const websiteDownloadsDir = path.join(projectDir, "website", "downloads");
const packageJson = JSON.parse(await readFile(path.join(projectDir, "package.json"), "utf8"));

const releaseFiles = await readdir(releaseDir).catch(() => []);
const macArmFile = releaseFiles.find((file) => file.endsWith(".dmg") && file.includes("arm64"));
const macIntelFile = releaseFiles.find((file) => file.endsWith(".dmg") && file.includes("x64"));
const genericMacFile = releaseFiles.find((file) => file.endsWith(".dmg") && !file.includes("arm64") && !file.includes("x64"));
const exeFile = releaseFiles.find((file) => file.endsWith(".exe"));

if (!macArmFile && !macIntelFile && !genericMacFile && !exeFile) {
  console.log("No .dmg or .exe installers found in release/. Run a dist build first.");
  process.exit(0);
}

await rm(websiteDownloadsDir, { recursive: true, force: true });
await mkdir(websiteDownloadsDir, { recursive: true });

const manifest = {
  productName: "PlugPffft",
  version: packageJson.version,
  generatedAt: new Date().toISOString(),
  downloads: {}
};

function copyDownloadEntry(sourceFile, targetName, manifestKey) {
  const sourcePath = path.join(releaseDir, sourceFile);
  return copyFile(sourcePath, path.join(websiteDownloadsDir, targetName)).then(async () => {
    manifest.downloads[manifestKey] = {
      url: `./downloads/${targetName}`,
      filename: sourceFile,
      sizeBytes: (await stat(sourcePath)).size
    };
  });
}

if (macArmFile) {
  await copyDownloadEntry(macArmFile, "PlugPffft-latest-mac-arm64.dmg", "macArm64");
}

if (macIntelFile) {
  await copyDownloadEntry(macIntelFile, "PlugPffft-latest-mac-x64.dmg", "macX64");
}

if (genericMacFile && !macArmFile && !macIntelFile) {
  const sourcePath = path.join(releaseDir, genericMacFile);
  const targetName = "PlugPffft-latest-mac.dmg";
  await copyFile(sourcePath, path.join(websiteDownloadsDir, targetName));
  manifest.downloads.mac = {
    url: `./downloads/${targetName}`,
    filename: genericMacFile,
    sizeBytes: (await stat(sourcePath)).size
  };
}

if (exeFile) {
  const sourcePath = path.join(releaseDir, exeFile);
  const targetName = "PlugPffft-latest-windows.exe";
  await copyFile(sourcePath, path.join(websiteDownloadsDir, targetName));
  manifest.downloads.windows = {
    url: `./downloads/${targetName}`,
    filename: exeFile,
    sizeBytes: (await stat(sourcePath)).size
  };
}

await writeFile(
  path.join(websiteDownloadsDir, "manifest.json"),
  `${JSON.stringify(manifest, null, 2)}\n`,
  "utf8"
);

console.log("Prepared website/downloads with the latest installers.");
