import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

import {
  assetStyleChips,
  briefMakeabilityExportReady,
  briefMakeabilityGateHint,
  flattenIntentChoices,
  formatBriefDocument,
  formatMakeabilityProductionSummary,
  formatMakeabilityReviewDetails,
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
  assert.doesNotMatch(out, /content_class/);
  assert.doesNotMatch(out, /\*\*视角 \(view\)：\*\*/);
  assert.match(out, /\*\*sprite_a\*\*/);
});

test("formatBriefDocument shows view and content_class when declared", () => {
  const brief = {
    project: { title: "Layout Demo", description: "props", view: "side" },
    assets: [
      {
        name: "crate",
        type: "texture",
        description: "crate",
        content_class: "prop_static",
      },
    ],
  };
  const out = formatBriefDocument(brief, null);
  assert.match(out, /\*\*视角 \(view\)：\*\* side/);
  assert.match(out, /\*\*内容类 \(content_class\)：\*\* prop_static/);
});

test("formatBriefDocument shows scenes systems ui_panels as readable sections", () => {
  const brief = {
    project: {
      title: "钓鱼",
      description: "短总览",
      gameplay_loop: "抛竿卖鱼",
      scenes: [
        {
          id: "dock",
          title: "钓场",
          summary: "抛竿搏鱼",
          ui_panel_ids: ["sell"],
        },
      ],
      systems: [{ id: "economy", title: "经济", summary: "票价与卖价" }],
      ui_panels: [
        {
          id: "sell",
          title: "出售弹层",
          kind: "popup",
          anchor: "center",
          slots: ["卖出", "入库"],
        },
      ],
    },
    assets: [
      {
        name: "鲫鱼",
        type: "character",
        description: "carp",
        scene_ids: ["dock"],
        system_ids: ["economy"],
      },
    ],
  };
  const out = formatBriefDocument(brief, null);
  assert.match(out, /## 场景（有进出的屏）/);
  assert.match(out, /\*\*钓场\*\* \(`dock`\)/);
  assert.match(out, /抛竿搏鱼/);
  assert.match(out, /UI 面板：`sell`/);
  assert.match(out, /## 逻辑系统（跨场景）/);
  assert.match(out, /\*\*经济\*\* \(`economy`\)/);
  assert.match(out, /## UI 面板/);
  assert.match(out, /\*\*出售弹层\*\*/);
  assert.match(out, /内容块：卖出、入库/);
  assert.match(out, /归属场景 \(scene_ids\)/);
  assert.match(out, /归属系统 \(system_ids\)/);
  assert.doesNotMatch(
    formatBriefDocument({ project: { title: "Plain" }, assets: [] }, null),
    /场景（有进出的屏）/,
  );
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
  const heroC = (exampleBrief.assets as Record<string, unknown>[]).find(
    (a) => a.name === "hero_c",
  )!;
  const chips = assetStyleChips(heroC);
  assert.ok(chips.some((c) => c.includes("cast_demo")));
  assert.ok(chips.some((c) => c.includes("hero_a")));
  assert.ok(chips.some((c) => c.includes("img2img")));
  assert.deepEqual(assetStyleChips({ name: "plain" }), []);
  assert.deepEqual(assetStyleChips({ name: "crate", content_class: "prop_static" }), [
    "类:prop_static",
  ]);
});

test("briefMakeabilityExportReady gates on review fingerprint and intent", () => {
  const base = {
    exists: true,
    ready_to_export: true,
    has_review: true,
    makeability_fingerprint_match: true,
    intent_count: 0,
  };
  assert.equal(briefMakeabilityExportReady(base), true);
  assert.equal(briefMakeabilityExportReady({ ...base, has_review: false }), false);
  assert.equal(briefMakeabilityExportReady({ ...base, makeability_fingerprint_match: false }), false);
  assert.equal(briefMakeabilityExportReady({ ...base, intent_count: 2 }), false);
});

test("briefMakeabilityGateHint explains blocked export", () => {
  assert.match(briefMakeabilityGateHint({ exists: true, has_review: false }), /制作审查/);
  assert.match(
    briefMakeabilityGateHint({
      exists: true,
      has_review: true,
      makeability_fingerprint_match: false,
    }),
    /重新/,
  );
});

test("flattenIntentChoices dedupes choices from intent gaps", () => {
  assert.deepEqual(
    flattenIntentChoices([
      { choices: ["A", "B"] },
      { choices: ["B", "C"] },
    ]),
    ["A", "B", "C"],
  );
});

test("formatMakeabilityReviewDetails lists intent and detail gaps", () => {
  const out = formatMakeabilityReviewDetails({
    intent_gaps: [{ id: "win", question: "How to win?", why_blocking: "blocks export" }],
    detail_gaps: [{ id: "bite", topic: "bite rate" }],
  });
  assert.match(out, /意图缺口/);
  assert.match(out, /How to win/);
  assert.match(out, /施工细节/);
  assert.match(out, /bite rate/);
});

test("formatMakeabilityProductionSummary reads production_doc.makeability", () => {
  assert.equal(
    formatMakeabilityProductionSummary({
      makeability: { status: "pending", detail_items: [{ id: "a" }, { id: "b" }] },
    }),
    "制作完备性：pending · 2 条施工细节",
  );
  assert.equal(formatMakeabilityProductionSummary({}), null);
});
