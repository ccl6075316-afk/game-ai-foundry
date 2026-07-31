# Release 打包与发布

面向**最终用户**的 Release **不依赖**本机已安装的 Python / Node。构建机需要 Python 3.11+、Node 20+。

## 用户侧（纯净电脑）

1. 下载 Release 产物：
   - **Windows（推荐）**：`*-setup.exe`（NSIS，可选安装目录、可卸载卸干净、**支持应用内自动更新**）
   - **Windows 亦可**：zip / portable（需手动换包）
   - **macOS**：zip（手动解压；首次可能需「仍要打开」；**暂无应用内自动更新**）
2. 安装 / 解压并运行 **Game AI Foundry**
3. 首次启动：
   - **设置** → 从示例创建 → 填 **OpenRouter** Key（做视频再填 Seedance）
   - 等待 **FFmpeg / Godot / .NET** 自动安装完成（顶部环境芯片变绿）
   - **（推荐）环境 → 执行器** → 按步骤配 Hermes / Codex / Cursor
4. `/brief` → `/plan` → `/run --run-prompts`

**不需要**：`pip install`、`npm install`、安装 Python、安装 Node、单独安装 rembg。

### 自动更新（仅 Windows 安装版）

产品策略：**先做好 Windows**；macOS 等有 Apple 开发者账号（签名+公证）后再做应用内更新。

- **支持自动更新**：Windows **NSIS `*-setup.exe`**（`electron-updater` 读 GitHub Releases 的 `latest.yml`）
- **不支持自动更新**：Windows zip / portable、**macOS**、Linux — 请到 Releases 手动下新包替换
- 启动约 12 秒后后台检查；有新版会下载，顶栏提示 **重启安装**。也可 **设置 → 本机 → 应用更新**
- 自动**升级**不会清掉 `~/.gamefactory/` 与工作区；**卸载**才会卸干净（见下）
- 发版机：`PUBLISH=1 GH_TOKEN=… ./scripts/build-release.sh`（需上传 `latest.yml`；Mac 元数据可有可无，当前客户端不会用）

### Windows NSIS 安装 / 卸载

- 安装向导可选：**安装目录**（`allowToChangeInstallationDirectory`）；默认当前用户安装（`selectPerMachineByDefault: false`，仍可提升权限）
- 开始菜单 + 桌面快捷方式；「应用和功能」里可卸载
- **卸载会尽量卸干净**（升级安装时不删用户数据）：
  - 安装目录
  - `%APPDATA%\game-ai-foundry-gui`（含 workspace）
  - `%LOCALAPPDATA%\game-ai-foundry-gui`（缓存）
  - `%USERPROFILE%\.gamefactory`（config、toolchain、API Key 等）
- 外置 Godot 工程目录（用户自己选的盘符路径）**不会**随卸载删除

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
| Hermes / Codex / Cursor | **设置 → 环境** 分步安装（推荐，非必需起步） |

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

1. `scripts/prepare_embedded_python.py --with-rembg` — **可迁移**独立 CPython 拷贝（含 rembg）；**禁止**用不可迁移的 `venv`（Windows `pyvenv.cfg home=` 会指向打包机）
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
> Pi 优先用系统 / PATH 上的 Node（≥22.19）；没有够新的 Node 时才用 `ELECTRON_RUN_AS_NODE` 复用 GUI Electron（避免 macOS 每次回答闪 Dock）。Electron 需 ≥36.9 / 37.5 / 39。

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
