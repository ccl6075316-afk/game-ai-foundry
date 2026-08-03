# 工程 Spec 增量：IT 只读加宽（会话 / 工程文件 / 本地配置）

## 执行元数据

- **Status**：confirmed（用户 2026-08-03：「需要有全部的读权限，不要把 IT 权限收到太窄」）
- **Workflow Stage**：code
- **Parent**：[`docs/superpowers/specs/2026-07-29-it-expanded-home-ops-design.md`](../../superpowers/specs/2026-07-29-it-expanded-home-ops-design.md)
- **Created**：2026-08-03

## 目标

IT（Pi + `FOUNDRY_TOOL`）在**仍无 shell、仍不改源码**的前提下，获得**加宽的只读**能力：

1. 列出 / 读取 `plans/conversations/{brief,it,programmer,product_host}/…` 会话（含近 N 条消息）
2. 列出 / 读取仓库内工程与运维相关文件（`projects/`、`plans/`、`output/`、以及仓库内其它文本），带体积上限
3. 读取 `~/.gamefactory/`（含 config），**密钥字段脱敏**
4. 白名单增加对应只读前缀；**不**因此放宽任意写盘 / shell / 改 `gui|cli|games` 源码

## 非目标

- 任意 shell（`bash`/`cat` 系统路径）
- 读任意家目录或系统日志目录（仅 `~/.gamefactory` + 仓库根内）
- 变更类权限变化（mutate 仍走现有 `--i-confirm` / 信任本会话）

## 验收

- `conversations list|show`、`inspect list|read` CLI + IT 白名单可用
- 路径逃逸（`..`、符号链接跳出根）拒绝
- `config.json` 读出无明文 `api_key`
- 单测覆盖脱敏与逃逸
