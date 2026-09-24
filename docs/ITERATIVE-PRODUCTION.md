# 迭代式 Production

> 目标：把“改需求”变成可审阅、可合并、可回归的文件变化。

## 1. 文档链

```text
Vision / intent
  → frozen brief.json
  → production.json
  → Change Request
  → Production Delta
  → apply-delta
  → progress / handoff
  → validation + regression
```

| 文档 | 回答的问题 | 是否可施工 |
|---|---|---|
| Vision / intent | 想做什么、长期方向 | 否 |
| frozen `brief.json` | 当前玩家体验、场景、系统、资产与验收 | 是 |
| `production.json` | 当前 slice 如何实现 | 是 |
| Change Request | 用户改变了什么意图 | 否，先分析 |
| Production Delta | 本次要新增/修改哪些任务与验收 | 是，合并后 |
| validation report | 新旧行为是否通过 | 证据 |

## 2. Brief 是冻结契约

外部 Agent 负责创意补全、取舍和字段修订；冻结后下游只读该文件。

```bash
python gamefactory.py brief validate --brief <brief> --json
python gamefactory.py production validate --production <production> --brief <brief> --json
```

若变化只影响实现细节，可直接进入 Production Delta；若改变玩家体验、场景、系统或资产范围，先更新 Brief 并重新冻结。

## 3. Slice 与范围

复杂游戏必须切片。当前 slice 至少明确：

- 目标场景与入口。
- 必须工作的系统。
- 必需资产。
- 会话目标与核心循环。
- 本次时长/进度边界。
- acceptance criteria 与 regression checks。

未来区域、长期成长、未选系统保留在 intent 文档，不提前施工。

## 4. Change Request

一次 Change Request 只描述用户意图、原因和期望体验，不直接写代码任务。

```bash
python gamefactory.py production delta \
  --change-id 002-add-double-jump \
  --intent "允许二段跳，并保持现有平台间距可通关" \
  --asset hero \
  --task double-jump \
  -o plans/changes/002-add-double-jump.production-delta.json \
  --json
```

审阅 Delta：

- 是否只改当前 slice。
- 是否引用稳定 `id`。
- 是否新增必要资产与任务依赖。
- 是否新增 acceptance criteria。
- 是否声明需要保护的 regression checks。

## 5. 合并与续作

```bash
python gamefactory.py production apply-delta \
  --delta <delta> --production <production> --dry-run --json

python gamefactory.py production apply-delta \
  --delta <delta> --production <production> --progress <progress> --json

python gamefactory.py project progress sync \
  --production <production> --progress <progress>
```

- `--dry-run` 只验证，不写。
- 合并成功后把新增/变更 `godot_tasks[]` 同步到 `progress`。
- 需要资产变化时重新 `pipeline plan --merge`，保留未受影响 task 状态。
- 为每个施工范围创建 `handoff`，记录权威来源与完成条件。

## 6. 验证必须回看设计

最低验证层：

1. Build：`godot validate` 成功。
2. Scene：main scene 加载、控制可用。
3. Functional：核心循环、胜负、关键系统按 Brief 工作。
4. Visual：截图/视频符合 visual target 与风格约束。
5. Regression：已接受旧行为没有退化。

```bash
python gamefactory.py test unit --project <project>
python gamefactory.py test plan --brief <brief> -o <playtest>
python gamefactory.py test play --project <project> --plan <playtest> --brief <brief>
python gamefactory.py test regression --project <project> --production <production>
```

Validation report 应引用失败的 Brief/Delta 条款，而不是只写“build failed”。

## 7. 失败后的分流

| 失败性质 | 下一步 |
|---|---|
| 实现偏离 Production | 修改对应 `godot_tasks[]`，保留验收 |
| Production 漏掉 Brief 规则 | 修 Production 或创建 Delta |
| 用户改变体验目标 | 新 Change Request → 更新 Brief → 新 Delta |
| 资产不合格 | 修 prompt/输入 → `workflow resume` → `status=done` 且 `next_action=human_review` → assets review |
| 旧功能退化 | 修复实现，不删除 regression check |
| 验收标准本身错误 | 明确提出设计变更，不能静默放宽 |

## 8. 续作账本

```bash
python gamefactory.py project progress show --progress <progress> --json
python gamefactory.py project progress note --progress <progress> "<note>"
python gamefactory.py project progress validation --progress <progress> --layer unit --status fail
python gamefactory.py project handoff list --json
python gamefactory.py project handoff status <handoff_id> --set open
```

跨会话恢复顺序：

1. `workflow context` / `status`。
2. `production show`。
3. `project progress show`。
4. `project handoff list/show`。
5. validation report。
6. 再选择任务。

## 9. 不可协商规则

1. 用户问题优先谈体验，不让实现数字取代设计意图。
2. Brief 描述目标，Production 描述实现。
3. 每次 Change 都先形成可审阅的意图与 Delta。
4. 施工只做当前 slice。
5. 实现必须保留已接受行为。
6. 验证同时检查新条件与旧回归。
7. 文件是契约，会话记忆不是契约。
8. Godot 不越 Brief / Delta 范围。

相关文档：[`CONSTRUCTION-SYSTEM.md`](CONSTRUCTION-SYSTEM.md)、[`AI-HANDOFF.md`](AI-HANDOFF.md)、[`README.md`](README.md)。
