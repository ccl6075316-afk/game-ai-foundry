import assert from "node:assert/strict";
import test from "node:test";
import { mergeSceneVisualRefsFromShards } from "./visualTargetHydrate.mjs";

test("mergeSceneVisualRefsFromShards reads visual_reference from catalog path shards", () => {
  const files = {
    "/proj/scenes/main_hub.json": JSON.stringify({
      id: "main_hub",
      visual_reference: "projects/demo/output/visual-target/main_hub/selected.png",
    }),
  };
  const io = {
    join: (...parts) => parts.join("/").replace(/\/+/g, "/"),
    existsSync: (p) => Boolean(files[p]),
    readFileSync: (p) => files[p],
  };
  const out = mergeSceneVisualRefsFromShards(
    [
      { id: "main_hub", title: "主界面", path: "scenes/main_hub.json" },
      { id: "shop", title: "店", visual_reference: "already.png", path: "scenes/shop.json" },
    ],
    "/proj",
    io,
  );
  assert.equal(
    out[0].visual_reference,
    "projects/demo/output/visual-target/main_hub/selected.png",
  );
  assert.equal(out[1].visual_reference, "already.png");
});
