/**
 * Smoke-test media path helpers used by GUI gallery / Electron preview.
 * Run: node gui/scripts/test-media-paths.mjs
 */
import { existsSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "../..");

function toRepoMediaRel(absOrRel) {
  const norm = String(absOrRel || "").trim().replace(/\\/g, "/");
  if (!norm) return "";
  const projectsIdx = norm.indexOf("projects/");
  if (projectsIdx >= 0) return norm.slice(projectsIdx);
  const outputIdx = norm.indexOf("output/");
  if (outputIdx >= 0) return norm.slice(outputIdx);
  return norm.replace(/^\.\.\//, "");
}

function resolveMediaAbs(relOrAbs) {
  const raw = String(relOrAbs || "").trim();
  if (!raw) return null;
  const candidates = [];
  const push = (p) => {
    if (!p) return;
    const n = path.normalize(p);
    if (!candidates.includes(n)) candidates.push(n);
  };
  if (path.isAbsolute(raw)) push(raw);
  else {
    const rel = raw.replace(/\\/g, "/");
    push(path.join(root, rel));
    if (rel.startsWith("output/") || rel.startsWith("plans/") || rel.startsWith("games/")) {
      const projectsDir = path.join(root, "projects");
      if (existsSync(projectsDir)) {
        for (const name of readdirSync(projectsDir)) {
          push(path.join(projectsDir, name, rel));
        }
      }
    }
  }
  for (const candidate of candidates) {
    if (!existsSync(candidate) || !statSync(candidate).isFile()) continue;
    const rel = path.relative(root, candidate);
    if (rel.startsWith("..") || path.isAbsolute(rel)) continue;
    return candidate;
  }
  return null;
}

const abs =
  "E:\\game-ai-foundry\\projects\\black-whistle\\output\\visual-target\\candidate_a.png";
const cases = [
  ["abs windows", abs],
  ["toRepo from abs", toRepoMediaRel(abs)],
  ["BUG old truncated", "output/visual-target/candidate_a.png"],
  ["projects rel", "projects/black-whistle/output/visual-target/candidate_b.png"],
];

let failed = 0;
for (const [label, input] of cases) {
  const resolved = resolveMediaAbs(input);
  const ok = Boolean(resolved && existsSync(resolved));
  console.log(`${ok ? "OK" : "FAIL"}  ${label}`);
  console.log(`     in:  ${input}`);
  console.log(`     out: ${resolved || "(null)"}`);
  if (!ok) failed += 1;
}

const rel = toRepoMediaRel(abs);
if (rel !== "projects/black-whistle/output/visual-target/candidate_a.png") {
  console.log("FAIL  toRepoMediaRel expected projects/... got", rel);
  failed += 1;
} else {
  console.log("OK  toRepoMediaRel prefers projects/ over bare output/");
}

process.exit(failed ? 1 : 0);
