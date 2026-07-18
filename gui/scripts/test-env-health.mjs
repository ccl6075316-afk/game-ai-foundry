/**
 * Smoke test for env health summarizer logic (duplicated lightly for node).
 * Full logic lives in gui/src/settings/envHealth.ts — keep cases in sync.
 * Run: node gui/scripts/test-env-health.mjs
 */

function summarize(input) {
  const issues = [];
  if (!input.doctor) {
    issues.push({ id: "doctor-parse", severity: "error" });
  } else {
    if (!input.doctor.config?.exists) issues.push({ id: "config-missing", severity: "error" });
    if (input.doctor.config?.openrouter_key !== "set")
      issues.push({ id: "image-api-key", severity: "error" });
  }
  if (!input.toolchain) {
    issues.push({ id: "toolchain-parse", severity: "error" });
  } else {
    for (const id of input.toolchain.missing_required || []) {
      issues.push({ id: `tool-missing-${id}`, severity: "error" });
    }
  }
  const blocking = issues.filter((i) => i.severity === "error");
  return { ok: blocking.length === 0, blocking, issues };
}

let failed = 0;
const healthy = summarize({
  doctor: {
    config: { exists: true, openrouter_key: "set", seedance_key: "set" },
    capabilities: { image_api: true },
  },
  toolchain: { missing_required: [], components: [] },
});
if (!healthy.ok) {
  console.log("FAIL healthy should pass");
  failed++;
} else console.log("OK healthy");

const noKey = summarize({
  doctor: {
    config: { exists: true, openrouter_key: "missing", seedance_key: "missing" },
    capabilities: { image_api: false },
  },
  toolchain: { missing_required: [], components: [] },
});
if (noKey.ok || !noKey.blocking.some((i) => i.id === "image-api-key")) {
  console.log("FAIL missing API key not blocking", noKey);
  failed++;
} else console.log("OK missing API key blocks");

const brokenDoctor = summarize({ doctor: null, toolchain: null });
if (brokenDoctor.ok) {
  console.log("FAIL null doctor should fail");
  failed++;
} else console.log("OK null doctor fails");

process.exit(failed ? 1 : 0);
