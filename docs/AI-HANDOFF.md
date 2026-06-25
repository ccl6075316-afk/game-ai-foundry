# Game AI Foundry — AI Agent Handoff（2026-06-25）

> **读者**：后续接手的 AI Agent / 自动化编排器。本文档汇总截至 2026-06-25 的架构、配置、VPN、抠图流水线与已验证命令，无需翻阅完整对话历史即可继续工作。

---

## 1. 项目是什么

**Game AI Foundry**（`game-ai-foundry`）是一个 **纯 Python CLI** 游戏资产生成工具链：

- 通过 OpenRouter 调用图像/LLM API 生图、写 prompt
- 本地 OpenCV 做裁边、色键抠图、边缘校验（默认不依赖 rembg）
- 可选 Godot 项目初始化、视频生成（Seedance）

**仓库根目录**：`/Users/czl/projects/game-ai-foundry`  
**CLI 入口**：`cli/gamefactory.py`（在 `cli/` 目录下执行）

```
game-ai-foundry/
├── cli/                          # Python CLI（无 LLM 运行时依赖）
│   ├── gamefactory.py            # 主入口
│   ├── prompt_craft.py           # prompt-crafter 逻辑
│   ├── asset_pipeline.py         # 资产类型 → pipeline 元数据
│   ├── plan_io.py                # plan/handoff JSON 读写
│   ├── proxy_utils.py            # 代理解析与注入（必读）
│   ├── image_cmds.py             # trim / remove-bg / slice / resize / validate-matting
│   ├── matting_config.py         # matting 配置解析
│   ├── matting_validate.py       # 抠图边缘 QA
│   └── skill_loader.py           # Agent skill 加载
├── resources/
│   ├── config.example.json       # 配置模板（含 proxy + matting）
│   ├── skills/                   # 三 Agent 的 skill 文档
│   │   ├── orchestrator/         # pipeline.md, matting.md
│   │   ├── prompt-crafter/       # asset-planner.md, asset-gen.md
│   │   └── image-generator/      # generate.md
│   ├── test-brief-wasteland-5.json
│   └── test-brief-icons.json
├── docs/
│   └── AI-HANDOFF.md             # 本文件
└── output/                       # 生成产物（gitignored）
```

---

## 2. 三 Agent 架构

| Agent | Role ID | Skill 文件 | CLI 命令 | 职责 |
|-------|---------|-----------|----------|------|
| **Orchestrator** | `orchestrator` | `pipeline.md`, `matting.md` | 编排、后处理 | 读 brief、委派、跑 trim/remove-bg/validate |
| **Prompt Crafter** | `prompt-crafter` | `asset-planner.md`, `asset-gen.md` | `prompt craft` | LLM 写 prompt → 输出 plan JSON |
| **Image Generator** | `image-generator` | `generate.md` | `image generate` | 只调图像 API，不写 prompt |

### 标准端到端流水线

```bash
cd cli

# Step 1 — prompt-crafter
python gamefactory.py prompt craft \
  --brief ../resources/test-brief-wasteland-5.json \
  --asset scavenger_scout \
  -o ../plans/scavenger_scout.json

# Step 2 — image-generator
python gamefactory.py image generate \
  --plan-file ../plans/scavenger_scout.json \
  -o ../output/scavenger_scout.png \
  --validate

# Step 3 — orchestrator 后处理（顺序固定）
python gamefactory.py image trim \
  --input ../output/scavenger_scout.png \
  --output ../output/scavenger_scout_trimmed.png

python gamefactory.py image remove-bg \
  --input ../output/scavenger_scout_trimmed.png \
  --output ../output/scavenger_scout_nobg.png
# remove-bg 默认附带 validate-matting；失败 exit code 2

# 可选单独复检
python gamefactory.py image validate-matting \
  --input ../output/scavenger_scout_nobg.png
```

`asset_pipeline.py` 中各类资产的 `pipeline` 元数据已更新为：`generate_image` → `validate` → `trim` → `remove_bg (color)` → `validate_matting`。

---

## 3. VPN / 代理配置（必读）

### 3.1 环境背景

开发机使用 **Clash**（macOS），HTTP 代理端口 **`127.0.0.1:7897`**。  
OpenRouter（`openrouter.ai`）在中国大陆需走代理；**规则模式**下若 `openrouter.ai` 规则为 DIRECT，即使配置了 proxy 也会地区限制失败。

### 3.2 配置文件

路径：`~/.gamefactory/config.json`  
模板：`resources/config.example.json`

```json
{
  "image": {
    "model": "google/gemini-3.1-flash-image",
    "api_key": "YOUR_OPENROUTER_KEY",
    "api_base": "https://openrouter.ai/api/v1",
    "proxy": "http://127.0.0.1:7897"
  },
  "prompt": {
    "model": "deepseek/deepseek-chat",
    "api_key": "YOUR_OPENROUTER_KEY",
    "api_base": "https://openrouter.ai/api/v1",
    "proxy": "http://127.0.0.1:7897"
  },
  "matting": { "...": "见第 4 节" }
}
```

**`image` 与 `prompt` 段都要配 `proxy`**（prompt craft 用 LLM，image generate 用图像 API）。

### 3.3 代理解析优先级（`cli/proxy_utils.py`）

1. CLI `--proxy` 参数  
2. `config.json` 顶层 `proxy` 或 `image`/`prompt`/`video` 段内的 `proxy`  
3. 环境变量：`GAMEFACTORY_PROXY`、`http_proxy`、`https_proxy` 等  
4. macOS 系统代理（`scutil --proxy`，Clash 开启系统代理时可自动读到）

CLI 启动时调用 `activate_proxy(config)`，向进程注入 `http_proxy`/`https_proxy` 等，且 `requests.Session` 设置 `trust_env=False` 强制走配置的 proxy。

### 3.4 Clash 规则模式排错

| 现象 | 原因 | 处理 |
|------|------|------|
| 已配 proxy 仍报地区限制 | Clash 规则让 `openrouter.ai` 直连 | 在 Clash 规则加 `DOMAIN-SUFFIX,openrouter.ai,PROXY` |
| 同上 | 规则模式未命中代理 | 临时切 **全局模式** 验证 |
| 连接超时 | Clash 未启动或端口不对 | 确认 Clash 监听 `7897`，或改 config 端口 |

代码内错误提示（`region_error_hint()`）：
> 若已配置代理仍出现地区限制，可能是 Clash 规则模式下 openrouter.ai 走了直连。请在 Clash 规则中将 DOMAIN-SUFFIX,openrouter.ai 设为 PROXY，或临时切换全局模式。

### 3.5 环境变量备选

```bash
export GAMEFACTORY_PROXY=http://127.0.0.1:7897
export OPENROUTER_API_KEY=sk-or-...
```

---

## 4. 抠图 / 切图流水线（Matting）

### 4.1 术语（与用户沟通）

| 用户说法 | CLI | 含义 |
|----------|-----|------|
| 切图、裁边、去白边 | `image trim` | 按内容外接矩形裁掉四周白边 |
| 抠图、透明底 | `image remove-bg` | 白底 → 透明 PNG |
| 检查白边 | `image validate-matting` | 轮廓 1–2px 带检测白晕 |
| 拆 kit、网格切 | `image slice --mode grid` | icon_kit 网格拆分（**不是**切图） |

### 4.2 色键算法（默认 `--mode color`）

OpenCV 实现，**无 ML**，适合白底黑边精灵：

1. 四角采样背景色 → 亮度 + 色差候选背景像素  
2. **`key_scope`** 决定抠白范围（见下表）  
3. （仅 `exterior`）轮廓贴外缘 1px 白晕清理  
4. Morph：`erode` / `dilate` / `despeckle`  
5. 硬 alpha（0/255）+ 透明区 RGB 清零  

| `key_scope` | CLI | 行为 |
|-------------|-----|------|
| `exterior`（**默认**） | `--key-scope exterior` | 只抠与画布边缘连通的白色（魔术棒），**保留**角色内部浅色高光 |
| `global` | `--key-scope global` | 所有符合亮度/色差的白色变透明（含内部浅色） |

备选：`--mode ai` 使用 rembg（需 `pip install "rembg[cpu]"`，已从默认 requirements 移除）。

### 4.3 Matting 配置段

```json
"matting": {
  "trim": {
    "threshold": 240,
    "padding": 2
  },
  "color_key": {
    "threshold": 235,
    "fuzz": 24,
    "key_scope": "exterior",
    "morph_erode": 2,
    "morph_dilate": 1,
    "despeckle": 1
  },
  "validate_edges": {
    "edge_width": 2,
    "brightness_threshold": 220,
    "max_white_ratio": 0.01,
    "max_semi_transparent": 0
  }
}
```

CLI 参数覆盖 config：`--threshold`, `--fuzz`, `--erode`, `--dilate`, `--despeckle`, `--key-scope`。

### 4.4 边缘校验

`remove-bg` 默认 `--validate-edges`（color 模式）。失败时 **exit 2**，输出 JSON 诊断。

**不要为此重生成图**，按 escalation 调参重跑 `remove-bg`：

```bash
python gamefactory.py image remove-bg \
  --input trimmed.png --output nobg_v2.png \
  --erode 2 --dilate 1 --despeckle 1 --fuzz 24 --threshold 235
```

| 用户反馈 | 自动动作 |
|----------|----------|
| 白边、白晕 | `--erode 2`，`morph_erode: 2` |
| 白点碎屑 | `--despeckle 1` |
| 抠完太瘦 | 减 erode、加 dilate |
| 还有白底 | 先 `trim`，再 `--fuzz 24 --threshold 235` |
| 四周空白多 | 先 `trim` 再 `remove-bg` |

详细规则见 `resources/skills/orchestrator/matting.md`。

---

## 5. 已完成的开发与测试（2026-06-25）

### 5.1 Git 历史

| Commit | 内容 |
|--------|------|
| `a0fe3b4` | 三 Agent 流水线、`proxy_utils`、prompt craft / image generate handoff |
| **本次提交** | Matting 全栈：trim、color-key remove-bg、validate-matting、key_scope、config、skills |

### 5.2 生图测试（均已成功）

- 单角色：盗龙、老虎、狮子  
- 五角色末世套装（`resources/test-brief-wasteland-5.json`）  
  - `scavenger_scout`, `mutant_boar`, `drone_wasp`, `raider_brute`, `feral_hound`  
- 输出目录：`output/`、`output/wasteland5/`

### 5.3 抠图测试结果（wasteland5）

| 资产 | 默认参数 | 备注 |
|------|----------|------|
| scavenger_scout | ✅ | |
| drone_wasp | ✅ | |
| raider_brute | ✅ | |
| feral_hound | ✅ | |
| mutant_boar | 需加参 | `--erode 3 --fuzz 28` |

`key_scope` 对比（drone_wasp）：`global` 比 `exterior` 多透明约 3.5 万像素（内部近白区域），行为符合预期。

---

## 6. CLI 速查

```bash
cd cli && pip install -r requirements.txt

# Agent skills
python gamefactory.py context --brief ../resources/test-brief-wasteland-5.json --asset scavenger_scout

# 图像
python gamefactory.py image generate --plan-file ../plans/x.json -o ../output/x.png --validate
python gamefactory.py image trim -i raw.png -o trimmed.png
python gamefactory.py image remove-bg -i trimmed.png -o nobg.png
python gamefactory.py image remove-bg -i trimmed.png -o nobg.png --key-scope global
python gamefactory.py image validate-matting -i nobg.png
python gamefactory.py image slice -i kit.png --mode grid --rows 2 --cols 2 -o ../output/tiles/
python gamefactory.py image resize -i ./sprites/ -w 64 -h 64

# Prompt
python gamefactory.py prompt craft --brief brief.json --asset NAME -o plans/NAME.json
python gamefactory.py prompt scaffold --brief brief.json --asset NAME -o plans/NAME.json
```

---

## 7. 依赖

`cli/requirements.txt`：

```
click>=8.1.0
requests>=2.31.0
opencv-python-headless>=4.8.0
numpy>=1.24.0
# Optional AI matting: pip install "rembg[cpu]"
```

---

## 8. 给后续 AI 的操作原则

1. **生图问题** → 查 proxy / Clash 规则；不要先改抠图参数。  
2. **白边/抠图问题** → 按 `matting.md` escalation 调参重跑 `remove-bg`；不要重生成图。  
3. **切图** = `trim`；**拆 kit** = `slice --mode grid`；不要混用。  
4. **交付资产** → `remove-bg` 后必须通过 `validate-matting`。  
5. **内部高光被抠掉** → 确认 `key_scope` 为 `exterior`（默认）；若用户要全白透明才用 `global`。  
6. **读 skill** → `resources/skills/<role>/`；orchestrator 同时加载 `pipeline` + `matting`。

---

## 9. 待办 / 未实现

- [ ] README 仍写旧版 `slice --mode auto`、单步 `remove-bg`，可对照本文档更新  
- [ ] 动画 pipeline 的 batch matting 自动化 CLI 封装  
- [ ] CI 对 matting 回归测试（golden PNG + validate-matting）  
- [ ] `mutant_boar` 默认参数是否写入 config preset  

---

## 10. 关键文件索引

| 用途 | 路径 |
|------|------|
| 代理 | `cli/proxy_utils.py` |
| 抠图实现 | `cli/image_cmds.py` → `remove_bg_color_key()` |
| 配置解析 | `cli/matting_config.py` |
| 边缘 QA | `cli/matting_validate.py` |
| Pipeline 元数据 | `cli/asset_pipeline.py` |
| Orchestrator skill | `resources/skills/orchestrator/matting.md` |
| 配置模板 | `resources/config.example.json` |
| 测试 brief | `resources/test-brief-wasteland-5.json` |

---

*文档版本：2026-06-25 · 与 `main` 分支同步提交*
