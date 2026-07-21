# Release 打包与发布

面向**最终用户**的 Release **不依赖**本机已安装的 Python / Node。构建机需要 Python 3.11+、Node 20+。

## 用户侧（纯净电脑）

1. 下载 Release 产物（推荐 **portable** `.exe` 或 `.zip` / macOS `.dmg`）
2. 解压 / 运行 **Game AI Foundry**
3. 首次启动：
   - **设置** → 从示例创建 → 填 **OpenRouter** Key（做视频再填 Seedance）
   - 等待 **FFmpeg / Godot / .NET** 自动安装完成（顶部环境芯片变绿）
   - **（推荐）环境 → 执行器** → 按步骤配 Hermes / Codex / Cursor
4. `/brief` → `/plan` → `/run --run-prompts`

**不需要**：`pip install`、`npm install`、安装 Python、安装 Node、单独安装 rembg。

### 数据目录

| 安装方式 | 工作区（brief / output / games） |
|----------|----------------------------------|
| Windows portable | exe 同目录下 `data/` |
| Windows 安装版 (NSIS) | `%APPDATA%/game-ai-foundry-gui/workspace/` |
| macOS | `~/Library/Application Support/game-ai-foundry-gui/workspace/` |

用户配置仍在 `~/.gamefactory/config.json`。

### 本机工具（Release）

| 组件 | 用户操作 |
|------|----------|
| FFmpeg | **自动安装**（启动后台） |
| Godot .NET | **自动安装** → 写入 `godot.engine_path` |
| .NET SDK | **自动安装** → `~/.gamefactory/toolchain/dotnet` |
| rembg | **内嵌 Python 自带**，无需操作 |
| **Pi（策划/IT 会话）** | **Release 内置**（复用 Electron Node ≥22.19）；只需配置 API Key |
| Hermes / Codex / Cursor | **环境面板分步安装**（推荐，非必需起步） |

详见 [`TOOLS.md`](TOOLS.md) · [`GUI-CONFIG.md`](GUI-CONFIG.md)

---

## 构建机：打 Release

### Windows

```bat
scripts\build-release.bat
```

### macOS / Linux

```bash
./scripts/build-release.sh
```

### 步骤说明

1. `scripts/prepare_embedded_python.py --with-rembg` — 内嵌 venv（含 rembg）
2. `scripts/prepare_embedded_pi.mjs` — 内嵌 pinned `@earendil-works/pi-coding-agent`（策划/IT 会话；**与 Electron 共用 Node**，不另打一份 Node）
3. `vite build` → `gui/dist/`
4. `electron-builder` — Electron **39+**（自带 Node ≥22.19，满足 Pi undici）+ 内嵌 Python + 内嵌 Pi + `cli/` + `resources/`

产物目录：`gui/release/`

| 平台 | 典型产物 |
|------|----------|
| Windows | `Game-AI-Foundry-*-portable.exe`、`*-setup.exe`、`.zip` |
| macOS | `Game-AI-Foundry-*-mac-arm64.dmg` |
| Linux | `Game-AI-Foundry-*-linux-x86_64.AppImage` |

> 内嵌 Python 与原生 wheel 需在**目标系统**上构建。  
> 内嵌 Pi 在构建机 `npm install` 到 `gui/runtime/pi`（已 gitignore）；冒烟：`python gamefactory.py setup pi smoke --json`。  
> Pi 通过 `ELECTRON_RUN_AS_NODE` 复用 GUI 的 Electron Node（需 ≥22.19；Electron 33 的 Node 20 不够）。

### 仅本地验证（不打包安装程序）

```bash
cd gui
npm run prepare:python
npm run prepare:pi
npm run build:app:dir
```

---

## 包内结构

```text
Game AI Foundry.app / Game AI Foundry.exe
├── resources/
│   ├── python/          # 内嵌 Python + OpenCV + rembg
│   └── gamefactory/
│       ├── cli/
│       └── resources/
└── (asar) dist + electron
```

运行时复制到用户工作区：`cli/`、`resources/`（保留用户 brief），并创建 `output/`、`games/`、`pipeline/`、`plans/`。

---

## 开发模式 vs Release

| | 开发 (`npm run dev`) | Release |
|--|---------------------|---------|
| 前端 | Vite 热更新 | `dist/` |
| Python | 系统 / `.venv` / `gui/runtime/python` | `resources/python` |
| rembg | `npm run prepare:python` 可选 | 构建时 `--with-rembg` |
| 工具链 | `setup install` 或 GUI 自动装 | 同左 |

---

## 发布检查清单

- [ ] 目标 OS 上完整跑通 `build-release`
- [ ] 纯净 VM：填 API Key → 等工具链自动装好 → `/brief` → `/run` 静图
- [ ] 环境 → 执行器：Hermes skills + API 同步；Codex login
- [ ] 附版本说明与最低系统版本（Win10+ / macOS 12+）
