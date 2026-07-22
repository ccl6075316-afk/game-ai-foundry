# 工程 Spec：Phase 2 — project.art_tokens

## 执行元数据

- **Status**：confirmed
- **Workflow Stage**：code（executed）
- **Created**：2026-07-22
- **Updated**：2026-07-22（T1+T2 落地；未 commit）
- **Confirmed By**：user「a」「a」；plan「确认」
- **Source Of Truth Until**：已实现；后续以代码 + AI-HANDOFF 为准；Phase 3 GUI 另开
- **Compounded Knowledge**：[`docs/solutions/architecture/style-group-img2img-and-art-tokens-20260722.md`](../../solutions/architecture/style-group-img2img-and-art-tokens-20260722.md)
- **Requirements Source**：style-ref-enhance Phase 2；Grill 字段 A、可选 A
- **Background Inputs**：[`2026-07-22-style-ref-enhance.md`](2026-07-22-style-ref-enhance.md)

## 工程理解

在 `project` 上增加可选结构化 **`art_tokens`**，与必填 `art_direction` 并存。  
有则在 `build_role_context` / visual-target context 中注入，供 prompt-crafter 写成硬锁；无则行为同今日。

## 目标

1. Brief：`project.art_tokens` 对象，已知键：`line` / `palette` / `forbid` / `silhouette`；未知键透传。 **Code Status**：done  
2. 解析/序列化；类型错误 audit；缺省不报错。 **Code Status**：done  
3. `project_to_dict` / role context 注入。 **Code Status**：done  
4. Skills 优先 tokens → style_lock。 **Code Status**：done  
5. 旧 brief 兼容。 **Code Status**：done  

## 非目标

- GUI（Phase 3）— **Code Status**：not applicable  
- 强制 export — **Code Status**：not applicable  
- 删除 `art_direction` / LoRA — **Code Status**：not applicable  

## 成功标准

1. context 含 art_tokens — **Code Status**：done（test_build_role_context）  
2. 无字段兼容 — **Code Status**：done  
3. palette string[] round-trip — **Code Status**：done  
4. skills 更新 — **Code Status**：done  

## 决策账本

| 已确认 | 小字典；可选；与 art_direction 并存 |

## Resume

实现完成（pause，未 commit）。下一步：review/commit 或 Phase 3。  

