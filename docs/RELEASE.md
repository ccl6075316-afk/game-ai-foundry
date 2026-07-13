# Release 打包与发布

面向**最终用户**的 Release **不依赖**本机已安装的 Python / Node。构建机需要 Python 3.11+、Node 20+。

## 用户侧（纯净电脑）

1. 下载 Release 产物（推荐 **portable** `.exe` 或 `.zip`）
2. 解压 / 运行 `Game AI Foundry.exe`
3. 首次启动：
   - 环境工具栏检测（FFmpeg 可一键安装）
   - **设置** 中填写 OpenRouter / 视频 API Key
   - （可选）下载 [Godot .NET 便携 zip](https://godotengine.org/download) 并指定路径
4. `/brief` → `/plan` → `/run --run-prompts`

**不需要**：`pip install`、`npm install`、安装 Python、安装 Node。

### 数据目录

| 安装方式 | 工作区（brief / output / games） |
|----------|----------------------------------|
| Windows portable | exe 同目录下 `data/` |
| Windows 安装版 (NSIS) | `%APPDATA%/game-ai-foundry-gui/workspace/` |
| macOS | `~/Library/Application Support/game-ai-foundry-gui/workspace/` |

用户配置仍在 `~/.gamefactory/config.json`。

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

1. `scripts/prepare_embedded_python.py` — 在 `gui/runtime/python` 创建内嵌 venv（含 `cli/requirements.txt`，默认带 rembg）
2. `vite build` — 前端静态资源 → `gui/dist/`
3. `electron-builder` — 打包 Electron + 内嵌 Python + `cli/` + `resources/`

产物目录：`gui/release/`

| 平台 | 典型产物 |
|------|----------|
| Windows | `Game-AI-Foundry-0.1.0-portable.exe`、`Game-AI-Foundry-0.1.0-setup.exe` |
| macOS | `Game-AI-Foundry-0.1.0-mac-arm64.dmg` |
| Linux | `Game-AI-Foundry-0.1.0-linux-x86_64.AppImage` |

> **跨平台**：内嵌 Python 与原生 wheel（OpenCV 等）需在**目标系统**上构建，不能在一台机器交叉打出所有平台包。

### 仅本地验证（不打包安装程序）

```bash
cd gui
npm run prepare:python
npm run build:app:dir
# 运行 gui/release/mac-arm64/Game AI Foundry.app 或 win-unpacked/*.exe
```

---

## 包内结构

```text
Game AI Foundry.app / Game AI Foundry.exe
├── resources/
│   ├── python/          # 内嵌 Python + site-packages
│   └── gamefactory/
│       ├── cli/         # gamefactory.py 及模块
│       └── resources/   # 示例 brief、skills、config.example
└── (asar) dist + electron
```

运行时复制到用户工作区：`cli/`、`resources/`（保留用户 brief），并创建 `output/`、`games/`、`pipeline/`、`plans/`。

---

## 开发模式 vs Release

| | 开发 (`npm run dev`) | Release |
|--|---------------------|---------|
| 前端 | Vite 热更新 | `dist/` 静态文件 |
| Python | 系统 / `.venv` | `resources/python` |
| 仓库根 | `gui/../` | 用户工作区 |
| 启动 | `start-gui.bat` | 双击 exe |

---

## 发布检查清单

- [ ] 在目标 OS 上完整跑通 `build-release`
- [ ] 纯净 VM：双击 exe → 填 API Key → `/brief` → `/run` 静图任务
- [ ] 环境工具栏 FFmpeg 一键安装
- [ ] Godot 下载链接 + 设置路径
- [ ] 附 `CHANGELOG` 与最低系统版本（Win10+ / macOS 12+）
