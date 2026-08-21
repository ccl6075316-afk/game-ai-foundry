import assert from "node:assert/strict";
import test from "node:test";

import { mapVisualTargetStatusFromCli } from "./visualTargetStatusMap.mjs";

function parseJson(text) {
  return JSON.parse(String(text || "").trim());
}

test("runCli-shaped success (exitCode=0, no ok field) maps ready from CLI JSON", () => {
  // Regression: T5 wrongly checked `result.ok` which runCli never sets → always ready=false.
  const cliResult = {
    exitCode: 0,
    stdout: JSON.stringify({
      ok: true,
      ready: true,
      disk_marked: true,
      global_ready: false,
      global_has_selected_image: true,
      global_selected_id: "b",
      global_preview_path: "projects/fishing-2d/output/visual-target/selected.png",
      visual_reference: "",
      scenes: [
        {
          id: "main_hub",
          title: "主界面",
          visual_reference: "projects/fishing-2d/output/visual-target/main_hub/selected.png",
          ready: true,
          selected_id: "c",
          has_selected_image: true,
          marked: true,
          preview_path: "projects/fishing-2d/output/visual-target/main_hub/selected.png",
        },
      ],
    }),
    stderr: "",
  };

  // Prove the old bug condition would fire on this shape:
  assert.equal(cliResult.ok, undefined);
  assert.equal(!cliResult.ok, true);

  const mapped = mapVisualTargetStatusFromCli(cliResult, parseJson);
  assert.equal(mapped.ok, true);
  assert.equal(mapped.ready, true);
  assert.equal(mapped.global_ready, false);
  assert.equal(mapped.global_has_selected_image, true);
  assert.equal(mapped.scenes.length, 1);
  assert.equal(mapped.scenes[0].ready, true);
  assert.equal(
    mapped.scenes[0].preview_path,
    "projects/fishing-2d/output/visual-target/main_hub/selected.png",
  );
});

test("nonzero exitCode returns ready=false", () => {
  const mapped = mapVisualTargetStatusFromCli(
    { exitCode: 1, stdout: "", stderr: "boom" },
    () => null,
  );
  assert.equal(mapped.ok, false);
  assert.equal(mapped.ready, false);
  assert.match(String(mapped.error), /boom|failed/);
});

test("CLI payload ok:false returns ready=false", () => {
  const mapped = mapVisualTargetStatusFromCli(
    {
      exitCode: 0,
      stdout: JSON.stringify({ ok: false, error: "brief unreadable" }),
      stderr: "",
    },
    parseJson,
  );
  assert.equal(mapped.ok, false);
  assert.equal(mapped.ready, false);
  assert.equal(mapped.error, "brief unreadable");
});
