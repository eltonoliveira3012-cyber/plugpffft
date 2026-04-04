import { mkdir, readdir, readFile, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const rootDir = path.dirname(fileURLToPath(import.meta.url));
const projectDir = path.resolve(rootDir, "..");
const sourceDir = path.join(projectDir, "src");
const distDir = path.join(projectDir, "dist");

async function collectTypescriptFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = await Promise.all(
    entries.map(async (entry) => {
      const fullPath = path.join(directory, entry.name);
      if (entry.isDirectory()) {
        return collectTypescriptFiles(fullPath);
      }

      if (entry.isFile() && entry.name.endsWith(".ts")) {
        return [fullPath];
      }

      return [];
    })
  );

  return files.flat();
}

await rm(distDir, { recursive: true, force: true });
await mkdir(distDir, { recursive: true });

const sourceFiles = await collectTypescriptFiles(sourceDir);

for (const sourceFile of sourceFiles) {
  const relativePath = path.relative(sourceDir, sourceFile);
  const outputPath = path.join(distDir, relativePath.replace(/\.ts$/, ".js"));
  const outputDir = path.dirname(outputPath);
  const sourceCode = await readFile(sourceFile, "utf8");

  const result = ts.transpileModule(sourceCode, {
    compilerOptions: {
      target: ts.ScriptTarget.ES2022,
      module: ts.ModuleKind.CommonJS,
      moduleResolution: ts.ModuleResolutionKind.NodeJs,
      esModuleInterop: true,
      strict: true
    },
    fileName: sourceFile
  });

  await mkdir(outputDir, { recursive: true });
  await writeFile(outputPath, result.outputText, "utf8");
}

console.log(`Transpiled ${sourceFiles.length} TypeScript files.`);
