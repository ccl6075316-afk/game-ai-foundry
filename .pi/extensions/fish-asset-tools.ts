/** Read-only Blender and Godot asset inspection tools for Pi agents. */
import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { Type } from "typebox";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { dirname, extname, isAbsolute, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { existsSync } from "node:fs";

const run = promisify(execFile);
const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const game = resolve(root, "projects/fishing-2d/game");
const blender = "E:\\blender\\blender.exe";
const godot = "E:\\Godot_v4.6.1-stable_mono_win64\\Godot_v4.6.1-stable_mono_win64_console.exe";
const blenderProbe = resolve(root, "resources/scripts/volume-fish/agent_asset_probe.py");
const godotProbe = "res://../experiments/agent-tools/inspect_fish.gd";

function withinRoot(path: string): boolean {
  const rel = relative(root, path);
  return rel !== "" && rel !== ".." && !rel.startsWith(`..${sep}`) && !isAbsolute(rel);
}

async function probe(exe: string, args: string[], marker: string, signal: AbortSignal) {
  const { stdout, stderr } = await run(exe, args, {
    cwd: root,
    timeout: 45000,
    maxBuffer: 2 * 1024 * 1024,
    signal,
    windowsHide: true,
  });
  const line = stdout.split(/\r?\n/).find((row) => row.startsWith(marker));
  if (!line) throw new Error(`Inspector produced no JSON receipt: ${stderr.slice(-800)}`);
  return JSON.parse(line.slice(marker.length));
}

export default function (pi: ExtensionAPI) {
  pi.registerTool({
    name: "inspect_blender_fish",
    label: "Inspect Blender fish",
    description: "Read mesh, UV, material, rig and action counts from a .blend or .glb inside Game AI Foundry. Does not edit the asset.",
    parameters: Type.Object({ path: Type.String({ description: "Workspace-relative .blend or .glb path" }) }),
    async execute(_id, params, signal) {
      const asset = resolve(root, params.path);
      if (!withinRoot(asset) || !existsSync(asset) || ![".blend", ".glb"].includes(extname(asset).toLowerCase())) {
        throw new Error("Asset must be an existing .blend or .glb inside this workspace");
      }
      const result = await probe(blender, ["--background", "--python", blenderProbe, "--", asset], "AGENT_FISH_PROBE ", signal);
      return { content: [{ type: "text", text: JSON.stringify(result) }], details: result };
    },
  });

  pi.registerTool({
    name: "inspect_godot_fish",
    label: "Inspect Godot fish",
    description: "Cold-read the imported fish GLB in Godot and report actual mesh arrays, materials, skeleton and animations. Does not run static builders or save assets.",
    parameters: Type.Object({ species: Type.String({ description: "Fish asset stem, for example african_catfish" }) }),
    async execute(_id, params, signal) {
      const species = params.species;
      if (!/^[A-Za-z][A-Za-z0-9_]*$/.test(species) || !existsSync(resolve(game, `assets/models/fish/${species}.glb`))) {
        throw new Error("Species must name an existing fish GLB");
      }
      const result = await probe(godot, ["--headless", "--path", game, "--script", godotProbe, "--", species], "AGENT_FISH_PROBE ", signal);
      return { content: [{ type: "text", text: JSON.stringify(result) }], details: result };
    },
  });
}
