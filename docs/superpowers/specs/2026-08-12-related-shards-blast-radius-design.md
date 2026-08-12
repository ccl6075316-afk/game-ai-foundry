# 设计：宿主计算的相关分册（blast radius）

## 状态

- **Status**：confirmed（用户 2026-08-12 口述确认：不靠人维护依赖表；不向量；图由宿主从已有字段 + id 提及算出；LLM 是消费者）
- **Code Status**：done（T1–T4 executed 2026-08-12）
- **Related**：
  - [`2026-08-10-document-focus-and-stable-ids.md`](./2026-08-10-document-focus-and-stable-ids.md)
  - [`2026-08-10-brief-catalog-shards-design.md`](./2026-08-10-brief-catalog-shards-design.md)
  - Plan：[`../../anvil/plans/2026-08-12-related-shards-blast-radius-plan.md`](../../anvil/plans/2026-08-12-related-shards-blast-radius-plan.md)

## 问题

Focus 写闸保证「本轮只改钉住的那一册」，但跨屏改动真实存在。LLM **不会稳定地**自己 `brief search` 检查连锁影响。人手维护 `dependency.json` 会错、会过期。

## 原则

1. **图不靠人维护。** 不新增依赖表。  
2. **宿主算边，模型消费。** 相关列表进策划 payload；不是 prompt 里「请自行判断影响」。  
3. **相关列表 ≠ 写许可。** v1 只告知，硬写闸不变。多册落盘仍走换 focus，或已有的 `intent_gap` / enrich 例外。  
4. **只读分册，禁止把展开稿写回 draft。**  
5. **不用向量 / 分词 / embedding。**

## v1 行为

有 `focus.kind ∈ {scene,system,asset}` 且能解析 id 时，`build_focus_context` 增加 `related_shards`（最多 12 条，不含自身）：

```json
{
  "kind": "scene",
  "id": "main_hub",
  "title": "主界面",
  "via": ["declared", "mention"],
  "path": "scenes/main_hub.json"
}
```

- **declared**：已有字段互指——`scene_ids` / `system_ids` / `ui_panel_ids` / `asset_ids`（分册正文或资产行）。反向：其它条目的这些字段包含当前 id。  
- **mention**：其它 catalog id 在当前分册正文中按 **id 词界**出现（`[^a-z0-9_]` 分隔，大小写不敏感）。**不用 title / 中文名当边。**  
- 无 focus / `project` / `visual_target` global / 加载失败：不捏造空「无关联」；focus 失败仍用现有 `focus_error`。related 计算失败 → `related_error` 字符串，列表省略。

策划 payload note 加一句：相关分册仅提示连锁，改它们须换 focus 或 `brief shard load` 后钉住；禁止凭列表 upsert 他册。

## 非目标（v1）

- 软工作区写闸 / 用户说「一并改」就放行多 path（可另开 v1.5）。  
- GUI 文档栏展示 related。  
- 制作审查替代或跳过。  
- 向量检索。  
- 把 related 分册全文注入（体积回退）。

## 验收

1. 资产 `scene_ids: ["main_hub"]` 且 focus=该资产 → related 含 `scene:main_hub`，`via` 含 `declared`。 **Code Status**：done
2. 场景正文提到 `` `combat` `` 或词界 `combat`，focus=该场景 → related 含 `system:combat`，`via` 含 `mention`。 **Code Status**：done
3. 改完正文不再提该 id → 下次 related 不再含 mention 边（declared 仍在则保留）。 **Code Status**：done
4. 策划轮 payload 有 related 列表、无他册 notes 全文。 **Code Status**：done
5. focus=scene A 时 upsert scene B 仍 `HostChatError`。 **Code Status**：done

## 非目标对照

| ❌ | ✅ |
|----|----|
| 人手 dependency 表 | 扫描已有字段 + id 提及 |
| 向量「语义像」 | 稳定 id |
| related 当写 allowlist | 只读提示 |
| hydrate 进 draft | 只读算完丢弃 |
