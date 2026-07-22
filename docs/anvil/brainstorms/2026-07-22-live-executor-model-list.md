# 工程 Spec：Codex / Cursor 模型列表改为 CLI 实时读取

## 执行元数据

- **Status**：confirmed
- **Workflow Stage**：code
- **Created**：2026-07-22
- **Updated**：2026-07-22
- **Source Of Truth Until**：实现以本 Spec + CLI/GUI 为准
- **Confirmed By**：user「改造吧 cursor 和 codex 一起改」（2026-07-22）— 否定假静态目录
- **Change Log**：相对模型档位 Spec A：取消「静态目录为选项源」；改为 CLI 发现；空列表不造假
- **Requirements Source**：用户批评「拉不到还硬写 UI 选项」；要求 Cursor + Codex 一并改
- **Background Inputs**：[`2026-07-21-executor-model-tiers-design.md`](../../superpowers/specs/2026-07-21-executor-model-tiers-design.md)；`agent --list-models`；`codex debug models`
- **Compounded Knowledge**：not yet

## 工程理解

「起了 CLI」不代表静态目录有用。选项必须来自**当前账号/安装下 CLI 能列出的模型**；列不出 → 空态 + 引导登录/安装，**禁止**再塞 Opus/Grok 等装饰项。

## 目标

1. **Cursor**：跑 `agent`/`cursor-agent --list-models`，解析可用 id；失败或「No models available」→ `ok` 带空 `models` + `hint`。  
2. **Codex**：跑 `codex debug models`（优先 JSON / 可加 `--bundled` 兜底），解析 slug/id；CLI 缺失或失败 → 空列表 + hint。  
3. CLI：`setup executor models --executor cursor|codex --json`。  
4. GUI：`ColleagueConfigBar` 原生路径改为 IPC 拉列表；下拉**仅**用返回的 models；高中低档仅当偏好 id **出现在实时列表**时才可点（否则隐藏或禁用该档）。  
5. 保留「自定义输入」仅当用户已有不在列表中的已存 model，或列表为空时允许手填（可选；默认：列表空时手填仍可用以免完全卡死）。  

## 非目标

- 不接 Cursor Cloud HTTP / `@cursor/sdk` 作为首期源（本机 CLI 优先）。  
- 不接 Codex app-server `model/list`（过重）。  
- 不恢复「未登录也展示完整假目录」为默认。  

## 验收

1. 单测：解析 fixture 文本/JSON → models；空文案 → models=[]。  
2. GUI：无模型时不出现静态假选项。  
3. 有模型时下拉等于 CLI 列表。  
4. `tsc` + 相关 unittest 绿。

## 市面同类（调研摘要，非实现范围）

| 形态 | 代表 | 与 Foundry 关系 |
|------|------|----------------|
| 官方编排 | OpenAI Agents SDK + `codex mcp-server` | 把 Codex 当 MCP 工具委派，不是游戏管线 GUI |
| IDE 内嵌 | Codex VS Code/JetBrains 扩展；Cursor IDE | 官方产品面，不是外包一层 Foundry |
| ACP 宿主 | Zed 等接 `agent acp` | mid-turn 协议客户端；Foundry B v2 后置方向 |
| CLI 代理 | [cursor-api-proxy](https://github.com/anyrobert/cursor-api-proxy) | 用 `agent --list-models` 填 `/v1/models`，与本改同思路 |
| SDK | `@cursor/sdk` / Cloud Agents `GET /v1/models` | 云端/账号列表；Foundry 现走本机 CLI |
| 社区 MCP | codex-as-mcp 等给 Claude Code 委派 | 多 Agent 委派，非游戏资产流水线 |

结论：市场上「把 Codex/Cursor 当本机执行器外包」多为 **MCP/ACP/SDK**；像 Foundry 这样「GUI 雇人 + `agent turn` one-shot」较少见。列表策略上，**cursor-api-proxy 与本改一致：信 CLI list**。

## Resume

- 下一步：实现 CLI + IPC + ConfigBar；用户要求时 commit。
