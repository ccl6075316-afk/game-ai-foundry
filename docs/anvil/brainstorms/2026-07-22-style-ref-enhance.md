# 工程 Spec：风格参考增强（终局 C / 本期 Phase 1=A）

## 执行元数据

- **Status**：confirmed
- **Workflow Stage**：req
- **Created**：2026-07-22
- **Updated**：2026-07-22（用户「ok」：终局 C、本期 A）
- **Confirmed By**：user「ok」（2026-07-22）
- **Source Of Truth Until**：Phase 1 plan 确认后由 plan 驱动 code；全量 C 完成前本 Spec 仍为终局事实源
- **Requirements Source**：市面对标建议；用户「按推荐补充」；Grill：长期 C 更合适 → 账本「终局 C / 本期 A」
- **Background Inputs**：[`2026-07-22-style-group-img2img.md`](2026-07-22-style-group-img2img.md)；OpenRouter：`image_config.strength` 主要 Recraft，Gemini 默认栈无可靠 API 强度
- **Compounded Knowledge**：Scenario Influence 偏低；MJ style/identity 分通道；Godogen 锚点+img2img 配方

## 背景输入

- `style_group` 已落地：组内默认 `--reference-image`，可关；视频/pose 正交。
- 市面更好处：style vs identity 拆开、偏低强度、分类配方、GUI 可见锚点；LoRA 不接当前 Gemini 栈。
- 用户确认：长远目标 **C**；本期只做 **A**，B/C 分阶段。

## 工程理解

在现有 style_group 上增加 **单参考图下的 style/identity 优先级**、**prompt 侧低强度默认**、**按资产类型的 pipeline 配方**，以及 **可选 config 强度透传（best-effort）**。  
后续 Phase 2：`art_tokens`；Phase 3：GUI 展示锚点/组/开关。

## 分期

| Phase | 内容 | 本期 |
|-------|------|------|
| **1 = A** | identity 优先级规则；prompt 软强度；分类配方；可选 strength 透传 | **做** |
| **2 = B** | `project.art_tokens` 结构化注入 craft | 不做 |
| **3 = C** | GUI 标锚点/组关系/开关状态 | 不做 |

## 目标（Phase 1）

1. Brief 资产可选 `identity_anchor`（name/id）：同角色变体身份锚。  
2. **单参考图解析优先级**（写死）：  
   - 若本资产需风格 img2img **且** 有有效 `identity_anchor` → 用 identity 图作 `--reference-image`；  
   - 否则走既有 `style_anchor` / `visual_reference` 规则；  
   - pose/video 仍只跟 `reference_asset`（本 Phase 不改）。  
3. Prompt/skill：**默认偏低强度**文案（借风格/身份，勿整图复制构图）；pipeline 不依赖 Gemini API strength。  
4. **配方表**（代码常量或 brief 可读默认）：哪些 `AssetType` 默认可走风格 img2img（character/prop/…）；icon_kit 等按表跳过或跟组（plan 定，默认：icon_kit 不因 style_group 自动 img2img，除非显式 follower 字段——与切片正交）。  
5. Config 可选 `image.style_img2img_strength`（0–1，默认 ~0.25）：若 provider/模型支持则透传 `image_config.strength`；不支持则忽略并短日志，**不失败**。  
6. 单测 + 文档短更；示例 brief 可加一行 identity 示例。

## 非目标（Phase 1）

- GUI（Phase 3）  
- `art_tokens`（Phase 2）  
- LoRA / 新图像 Provider 轨  
- 双参考图一次请求  
- 改变视频优先 / pose `reference_asset` 语义  
- 强制 Gemini 支持 strength（做不到）

## 当前架构约束

| 证据 | 含义 |
|------|------|
| `should_use_style_img2img` / `resolve_style_img2img_path` | 扩展解析，勿推翻 |
| OpenRouter strength ≈ Recraft | Gemini：prompt 软强度为主 |
| style_group Spec | 关系仍可选；本 Phase 增强参考语义 |

## 方案选择

| 决策 | 选择 |
|------|------|
| 终局 | C（规则+tokens+GUI） |
| 本期 | Phase 1 = A |
| 强度 | prompt 默认软低；API strength best-effort |
| 双锚 | 单槽：identity 优先于 style（当两者都适用时） |

## 边界与失败模式

| 场景 | 期望 |
|------|------|
| 仅有 style_group | 同今日 |
| 有 identity_anchor + style 组 | 参考图 = identity 资产 raw |
| identity 指向未知资产 | validate 报错 |
| strength 配置但模型不支持 | 忽略+日志，生成继续 |
| icon_kit | 按配方：默认不自动 style img2img（除非显式设计为 follower——plan 锁定） |

## 工程代价

- `brief.py` / `shared_context.py` / `pipeline_manifest.py` / `gamefactory.py`（可选 strength）  
- skills：prompt-crafter / image-generator  
- 测试：`test_style_group.py`  
- 文档短更  
- **预估**：小–中

## 成功标准（Phase 1）

1. 有 `identity_anchor` 的 follower：plan argv 参考图指向 identity raw，而非仅 style_anchor。  
2. 无 identity 时行为与 style_group v1 一致。  
3. skill/文档含「偏低强度、勿复制构图」。  
4. 配方表有单测或常量断言（至少 character 开、约定类型关）。  
5. 配置 strength 不导致 Gemini 路径硬失败。  

## 决策账本

| 状态 | 决策 |
|------|------|
| 已确认 | 终局 C |
| 已确认 | 本期仅 Phase 1=A |
| 已确认 | identity 优先于 style（单参考） |
| 已确认 | 强度：prompt 软 + API best-effort |
| 已确认 | Phase 2/3 本 Spec 记载、本期不做 |

## Resume

- **下一步**：`/anvil:plan`（Phase 1）→ 确认 → `/anvil:code`。  
- Phase 2/3 另开 plan 或本 Spec 续篇。  
