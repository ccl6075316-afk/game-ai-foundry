import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

import {
  assetStyleChips,
  briefMakeabilityExportReady,
  briefMakeabilityGateHint,
  catalogDisplayTitle,
  catalogRowsFromDraft,
  docsViewFromFocus,
  flattenIntentChoices,
  formatBriefCatalogOverview,
  formatBriefDocument,
  formatDocsViewLabel,
  formatFocusLabel,
  formatMakeabilityProductionSummary,
  formatMakeabilityReviewDetails,
  formatShardDocument,
  inlineShardFromDraft,
  isBriefShaped,
  mergeStatusFocus,
  shardEntryHasBody,
  shardRelPath,
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

test("briefMakeabilityExportReady gates on structural contract only", () => {
  const base = {
    exists: true,
    ready_to_export: true,
    contract_complete: true,
    gaps: [] as string[],
    has_review: false,
    makeability_fingerprint_match: false,
    intent_count: 2,
  };
  assert.equal(briefMakeabilityExportReady(base), true);
  assert.equal(briefMakeabilityExportReady({ ...base, gaps: ["asset id missing"] }), false);
  assert.equal(briefMakeabilityExportReady({ ...base, contract_complete: false, ready_to_export: false }), false);
});

test("briefMakeabilityGateHint keeps makeability advisory", () => {
  assert.match(
    briefMakeabilityGateHint({ exists: true, contract_complete: true, gaps: [], has_review: false }),
    /可保存/,
  );
  assert.match(
    briefMakeabilityGateHint({
      exists: true,
      contract_complete: true,
      gaps: [],
      has_review: true,
      makeability_fingerprint_match: false,
    }),
    /可保存/,
  );
  assert.match(
    briefMakeabilityGateHint({ exists: true, gaps: ["bad id"], contract_complete: false }),
    /校验未通过/,
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

test("formatBriefCatalogOverview lists shards without dumping notes", () => {
  const brief = {
    project: {
      title: "钓鱼",
      description: "短总览",
      scenes: [
        {
          id: "dock",
          title: "钓场",
          summary: "抛竿",
          notes: "超长正文不应进总览",
        },
      ],
      systems: [{ id: "economy", title: "经济", notes: "表级细则" }],
    },
    assets: [{ name: "carp", type: "character", description: "鱼" }],
  };
  const out = formatBriefCatalogOverview(brief, null);
  assert.match(out, /Brief 总览/);
  assert.match(out, /短总览/);
  assert.match(out, /点选不会改对话焦点/);
  assert.doesNotMatch(out, /超长正文不应进总览/);
  assert.doesNotMatch(out, /表级细则/);
  assert.doesNotMatch(out, /## 原始 JSON/);
  const rows = catalogRowsFromDraft(brief);
  assert.equal(rows.some((r) => r.id === "dock" && r.kind === "scene"), true);
  assert.equal(rows.some((r) => r.id === "economy"), true);
});

test("catalog rows and shard path helpers", () => {
  const rows = catalogRowsFromDraft({
    project: {
      scenes: [{ id: "hub", title: "主界面" }],
      systems: [{ id: "combat", title: "战斗" }],
    },
    assets: [{ name: "rod" }],
  });
  assert.equal(rows.length, 3);
  assert.equal(shardRelPath("projects/fishing-2d", "scene", "hub"), "projects/fishing-2d/scenes/hub.json");
  assert.equal(
    shardRelPath("projects/fishing-2d", "asset", "rod"),
    "projects/fishing-2d/assets/rod.spec.json",
  );
  assert.equal(
    shardRelPath("projects/fishing-2d", "asset", "x", "assets/bg_1.spec.json"),
    "projects/fishing-2d/assets/bg_1.spec.json",
  );
});

test("focus / docs view labels and mapping", () => {
  assert.equal(formatDocsViewLabel({ mode: "overview" }), "总览");
  assert.equal(formatDocsViewLabel({ mode: "shard", kind: "scene", id: "hub" }), "场景 · hub");
  assert.equal(
    formatDocsViewLabel({ mode: "shard", kind: "scene", id: "hub" }, "主界面"),
    "场景 · 主界面",
  );
  assert.equal(formatFocusLabel(null), "未钉住");
  assert.equal(formatFocusLabel({ kind: "scene", id: "hub" }), "场景 · hub");
  assert.equal(formatFocusLabel({ kind: "scene", id: "hub" }, "主界面"), "场景 · 主界面");
  assert.equal(catalogDisplayTitle({ id: "combat", title: "钓鱼战斗" }), "钓鱼战斗");
  assert.equal(catalogDisplayTitle({ id: "combat", title: "" }), "combat");
  assert.deepEqual(docsViewFromFocus({ kind: "scene", id: "hub" }), {
    mode: "shard",
    kind: "scene",
    id: "hub",
  });
  assert.deepEqual(docsViewFromFocus({ kind: "visual_target", id: "hub" }), {
    mode: "shard",
    kind: "scene",
    id: "hub",
  });
  assert.deepEqual(docsViewFromFocus({ kind: "project" }), { mode: "overview" });
  assert.match(
    formatShardDocument("scene", "hub", { title: "主界面", notes: "大厅" }),
    /## 备注 \/ 正文/,
  );
});

test("mergeStatusFocus keeps prev unless payload sets focus", () => {
  assert.deepEqual(
    mergeStatusFocus({ kind: "scene", id: "hub" }, undefined),
    { kind: "scene", id: "hub" },
  );
  assert.equal(mergeStatusFocus({ kind: "scene", id: "hub" }, null), null);
  assert.deepEqual(
    mergeStatusFocus({ kind: "scene", id: "hub" }, { kind: "system", id: "eco" }),
    { kind: "system", id: "eco" },
  );
});

test("inlineShardFromDraft falls back to draft body", () => {
  const draft = {
    project: {
      scenes: [{ id: "hub", title: "主界面", notes: "大厅细则" }],
      systems: [{ id: "eco", title: "经济" }],
    },
    assets: [{ id: "rod", name: "鱼竿", description: "木竿" }],
  };
  const scene = inlineShardFromDraft(draft, "scene", "hub");
  assert.ok(scene);
  assert.equal(scene!.notes, "大厅细则");
  assert.equal(shardEntryHasBody(scene), true);
  assert.equal(shardEntryHasBody(inlineShardFromDraft(draft, "system", "eco")), false);
  assert.equal(inlineShardFromDraft(draft, "asset", "rod")?.description, "木竿");
  assert.equal(inlineShardFromDraft(draft, "scene", "missing"), null);
});
