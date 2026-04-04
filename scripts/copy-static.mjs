import { copyFile, mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const rootDir = path.dirname(fileURLToPath(import.meta.url));
const projectDir = path.resolve(rootDir, "..");
const sourceHtml = path.join(projectDir, "src", "player", "player.html");
const distPlayerDir = path.join(projectDir, "dist", "player");
const targetHtml = path.join(distPlayerDir, "player.html");

await mkdir(distPlayerDir, { recursive: true });
await copyFile(sourceHtml, targetHtml);

console.log(`Copied ${path.relative(projectDir, sourceHtml)} -> ${path.relative(projectDir, targetHtml)}`);
