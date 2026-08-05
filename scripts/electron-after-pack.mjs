/**
 * electron-builder strips directories named `node_modules` from extraResources
 * by default — so runtime/pi arrives in the package without Pi's deps.
 * Copy them back after pack so GAMEFACTORY_PI_ROOT works in Release.
 */
import { cpSync, existsSync, mkdirSync, rmSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default async function afterPack(context) {
  const projectDir = context.packager.projectDir;
  const src = path.join(projectDir, "runtime", "pi", "node_modules");
  if (!existsSync(src)) {
    throw new Error(
      `afterPack: missing ${src} — run "npm run prepare:pi" before packaging`,
    );
  }

  const platform = context.electronPlatformName;
  let resourcesDir;
  if (platform === "darwin") {
    const name = context.packager.appInfo.productFilename;
    resourcesDir = path.join(
      context.appOutDir,
      `${name}.app`,
      "Contents",
      "Resources",
    );
  } else {
    resourcesDir = path.join(context.appOutDir, "resources");
  }

  const destRoot = path.join(resourcesDir, "pi");
  const dest = path.join(destRoot, "node_modules");
  if (!existsSync(destRoot)) {
    throw new Error(
      `afterPack: expected extraResources pi at ${destRoot} (missing package.json/manifest?)`,
    );
  }
  if (existsSync(dest)) {
    rmSync(dest, { recursive: true, force: true });
  }
  mkdirSync(dest, { recursive: true });
  console.log(`[afterPack] Copying Pi node_modules → ${dest}`);
  cpSync(src, dest, { recursive: true });
  const entry = path.join(
    dest,
    "@earendil-works",
    "pi-coding-agent",
    "dist",
    "cli.js",
  );
  if (!existsSync(entry)) {
    throw new Error(`afterPack: Pi entry missing after copy: ${entry}`);
  }
  console.log(`[afterPack] Pi entry OK: ${entry}`);
}
