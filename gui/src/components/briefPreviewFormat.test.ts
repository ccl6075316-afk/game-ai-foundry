import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

import {
  assetStyleChips,
  formatBriefDocument,
  isBriefShaped,
  tryFormatBriefJsonText,
} from "./briefPreviewFormat";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const examplePath = path.resolve(__dirname, "../../../resources/style-group-img2img.example.json");
const exampleJson = readFileSync(examplePath, "utf8");
const exampleBrief = JSON.parse(exampleJson);

test("isBriefShaped accepts project/assets brief", () => {
  assert.equal(isBriefShaped(exampleBrief), true);
  assert.equal(isBriefShaped({ foo: 1 }), false);
  assert.equal(isBriefShaped(null), false);
});

test("formatBriefDocument shows art_tokens and style fields", () => {
  const out = formatBriefDocument(exampleBrief, null);
  assert.match(out, /## 风格硬锁 \(art_tokens\)/);
  assert.match(out, /\*\*line：\*\* clean 2px outline/);
  assert.match(out, /\*\*palette：\*\* #2B2B2B/);
  assert.match(out, /\*\*风格组 \(style_group\)：\*\* cast_demo/);
  assert.match(out, /\*\*风格锚 \(style_anchor\)：\*\* hero_a/);
  assert.match(out, /\*\*身份锚 \(identity_anchor\)：\*\* hero_a/);
  assert.match(out, /\*\*风格 img2img \(use_style_img2img\)：\*\* 关/);
  assert.match(out, /## 原始 JSON/);
});

test("formatBriefDocument omits empty style sections for plain brief", () => {
  const plain = {
    project: { title: "Plain", description: "No style keys" },
    assets: [{ name: "sprite_a", type: "prop", description: "simple" }],
  };
  const out = formatBriefDocument(plain, null);
  assert.doesNotMatch(out, /风格硬锁/);
  assert.doesNotMatch(out, /style_group/);
  assert.match(out, /\*\*sprite_a\*\*/);
});

test("tryFormatBriefJsonText formats valid brief JSON", () => {
  const out = tryFormatBriefJsonText(exampleJson, null);
  assert.ok(out);
  assert.match(out!, /Style Group Demo|cast_demo/);
});

test("tryFormatBriefJsonText returns null for bad JSON", () => {
  assert.equal(tryFormatBriefJsonText("{not json", null), null);
  assert.equal(tryFormatBriefJsonText('{"foo":1}', null), null);
});

test("assetStyleChips lists declared style fields only", () => {
  const heroB = (exampleBrief.assets as Record<string, unknown>[]).find(
    (a) => a.name === "hero_b",
  )!;
  const chips = assetStyleChips(heroB);
  assert.ok(chips.some((c) => c.includes("cast_demo")));
  assert.ok(chips.some((c) => c.includes("hero_a")));
  assert.ok(chips.some((c) => c.includes("img2img")));
  assert.deepEqual(assetStyleChips({ name: "plain" }), []);
});
