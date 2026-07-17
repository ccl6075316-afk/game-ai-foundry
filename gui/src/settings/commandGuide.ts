export interface GuideCommand {
  title: string;
  command: string;
  description: string;
  note?: string;
}

export interface GuideSection {
  id: string;
  title: string;
  intro?: string;
  commands: GuideCommand[];
}

/** 对话指令 + CLI 命令说明（GUI 指南侧栏） */
export const COMMAND_GUIDE: GuideSection[] = [
  {
    id: "release",
    title: "Release 首次运行",
    intro: "使用打包好的 exe/dmg 时，无需安装 Python 或 Node。",
    commands: [
      {
        title: "启动应用",
        command: "双击 Game AI Foundry.exe",
        description: "portable 版工作区在 exe 旁 data/；安装版在系统 AppData",
      },
      {
        title: "① 配置 API（最低开工）",
        command: "设置 → 从示例创建 → 填写 OpenRouter Key → 保存",
        description: "即可 /brief、/plan、/run；视频需另配 Seedance",
      },
      {
        title: "② 等本机工具自动装好",
        command: "（启动后台自动执行）",
        description: "FFmpeg、Godot .NET、.NET SDK 缺失时会自动下载；rembg 已内嵌于打包 Python",
      },
      {
        title: "③ 推荐：配置执行器 Agent",
        command: "环境 → 执行器 → 按步骤安装 Hermes / Codex / Cursor",
        description:
          "仅 API 只能聊天+跑 pipeline；Agent 可排错、改配置、写玩法。详见 docs/TOOLS.md",
        note: "Hermes 同步当前生文 Provider；Codex 用于 C# 玩法开发",
      },
    ],
  },
  {
    id: "agents",
    title: "执行器 Agent（推荐）",
    intro:
      "GUI 主聊天 = LLM API + 固定斜杠命令；完整「带队、排错、写代码」需 Hermes / Cursor / Codex。外部 AI 代操请读 docs/TOOLS.md。",
    commands: [
      {
        title: "为什么需要 Agent",
        command: "（概念）",
        description:
          "无 Agent：可 Brief + pipeline 出资产，但不能根据自然语言自由跑 doctor、改 config、委派角色",
      },
      {
        title: "Hermes（推荐独立使用）",
        command: "环境 → Hermes：安装 CLI → Skills → 同步 API",
        description: "项目经理 / prompt-crafter / tester；装 game-factory-orchestrator skill",
      },
      {
        title: "Codex（写 C# 玩法）",
        command: "环境 → Codex：安装 CLI → 浏览器登录",
        description: "程序员角色 godot-developer；OpenAI 登录式，不用 OpenRouter Key",
      },
      {
        title: "Cursor（IDE 内带队）",
        command: "环境 → Cursor：下载 IDE → 检测 CLI",
        description: "在 Cursor 里读 resources/skills/ 改 games/ 代码",
      },
      {
        title: "CLI 检测执行器状态",
        command: "python gamefactory.py setup executor status --json",
        description: "分步安装进度；GUI 环境面板等效",
      },
      {
        title: "安装 Hermes Skills",
        command: "cd cli && python gamefactory.py hermes install",
        description: "写入 ~/.hermes/skills/；外部 Agent 应加载 orchestrator skill",
      },
      {
        title: "外部 Agent 操作手册",
        command: "docs/TOOLS.md",
        description: "配置、本机工具、纠错、JSON 探测命令 — 给其他 AI Agent 用",
      },
    ],
  },
  {
    id: "workflow",
    title: "推荐流程",
    intro: "从零到可玩：配 API →（推荐配 Agent）→ 策划 → 规划 → 生成 → 组装 → 开发玩法。",
    commands: [
      {
        title: "0. 配置 API",
        command: "设置 → Provider → 保存 OpenRouter Key",
        description: "最低门槛；生视频另配 Seedance",
      },
      {
        title: "0b. 配置 Agent（推荐）",
        command: "环境 → 执行器",
        description: "Hermes 带队排错；Codex/Cursor 写玩法 — 见「执行器 Agent」章节",
      },
      {
        title: "1. 策划 Brief",
        command: "/brief",
        description: "多轮对话澄清需求，导出 resources/{slug}-brief.json",
      },
      {
        title: "2. 生成流水线",
        command: "/plan",
        description: "根据当前 brief 生成 pipeline manifest",
      },
      {
        title: "3. 运行资产生成",
        command: "/run --run-prompts",
        description: "并行执行生图、视频、抠图、Godot 组装等任务",
      },
      {
        title: "4. 打开 Godot",
        command: "/godot",
        description: "用本机 Godot 打开 games/{slug} 工程",
      },
    ],
  },
  {
    id: "gui",
    title: "GUI 对话指令",
    commands: [
      { title: "环境面板", command: "/env", description: "打开侧栏：本机工具检测与一键安装" },
      { title: "命令指南", command: "/guide", description: "打开指南侧栏（GUI 指令 + CLI 速查）" },
      { title: "环境检测", command: "/doctor", description: "探测并打开环境侧栏" },
      { title: "看板", command: "/board", description: "打开 pipeline 任务 DAG 与日志" },
      { title: "设置", command: "/settings", description: "编辑 API Key、代理、Godot 路径" },
      { title: "仅运行（不 craft prompt）", command: "/run", description: "使用已有 plans/*.json 直接跑管线" },
    ],
  },
  {
    id: "env",
    title: "本机工具与环境",
    intro: "在仓库 cli/ 目录执行；GUI 工具栏可一键检测与安装。FFmpeg/Godot/.NET 缺失时启动自动安装。",
    commands: [
      {
        title: "检测全部准备项",
        command: "python gamefactory.py setup check --json",
        description: "FFmpeg、Godot、.NET 三项必需工具",
      },
      {
        title: "自动安装 Godot .NET",
        command: "python gamefactory.py setup install godot",
        description: "下载到 ~/.gamefactory/toolchain/godot 并写入 engine_path",
      },
      {
        title: "自动安装 FFmpeg",
        command: "python gamefactory.py setup install ffmpeg",
        description: "下载到 ~/.gamefactory/toolchain/bin",
      },
      {
        title: "自动安装 .NET SDK",
        command: "python gamefactory.py setup install dotnet",
        description: "下载到 ~/.gamefactory/toolchain/dotnet",
      },
      {
        title: "完整环境探测",
        command: "python gamefactory.py doctor --json",
        description: "执行器、Agent 路由、API Key、Godot 路径",
      },
      {
        title: "查看 Agent 路由",
        command: "python gamefactory.py agents show --discover",
        description: "七角色与推荐 executor",
      },
    ],
  },
  {
    id: "brief",
    title: "Brief 与策划",
    commands: [
      {
        title: "策划对话（主路径）",
        command: "python gamefactory.py brief chat start --json",
        description: "host-chat 多轮；落实后 brief chat export",
      },
      {
        title: "Brainstorm 导出（CLI 兼容）",
        command: "python gamefactory.py brief brainstorm export -o ../resources/my-game-brief.json",
        description: "问卷式 merge；GUI 默认已改用 brief chat",
      },
      {
        title: "Agent 同事 turn",
        command: "python gamefactory.py agent turn --role product_host --session-id demo --message \"试玩反馈...\" --json",
        description: "项目经理 / 程序员 → executor CLI；可写 handoff",
      },
      {
        title: "列出派工",
        command: "python gamefactory.py project handoff list --json",
        description: "plans/handoffs/ 未读与状态",
      },
      {
        title: "GUI 改需求",
        command: "/delta 002-double-jump | 增加二段跳",
        description: "项目经理/策划：创建 Delta 并合并进 production + progress",
      },
      {
        title: "创建 Production Delta",
        command:
          'python gamefactory.py production delta --change-id 002-double-jump --intent "增加二段跳" --task "实现二段跳"',
        description: "改需求施工切片；再 production apply-delta 合并进蓝图",
      },
      {
        title: "合并 Delta 到 production",
        command:
          "python gamefactory.py production apply-delta --delta ../plans/changes/002-double-jump.production-delta.json --production ../plans/production_my-game.json --progress ../plans/progress_my-game.json",
        description: "追加 godot_tasks 与验收标准；可加 --progress 同步任务账本",
      },
      {
        title: "同步 progress 任务",
        command:
          "python gamefactory.py project progress sync --progress ../plans/progress_my-game.json --production ../plans/production_my-game.json",
        description: "把 production 新增任务拉进 progress（跳过已有 id）",
      },
      {
        title: "执行白名单建议命令",
        command: 'python gamefactory.py project action --cmd "python gamefactory.py pipeline status --json"',
        description: "GUI「执行 · …」按钮同源；仅允许 pipeline/godot/test 等",
      },
      {
        title: "校验 brief",
        command: "python gamefactory.py brief validate --brief ../resources/my-game-brief.json",
        description: "检查 JSON 契约与必填字段",
      },
      {
        title: "Visual Target",
        command: "python gamefactory.py brief visual-target generate --brief ../resources/my-game-brief.json",
        description: "生成北极星参考图候选",
      },
    ],
  },
  {
    id: "pipeline",
    title: "Pipeline",
    commands: [
      {
        title: "规划 DAG",
        command: "python gamefactory.py pipeline plan --brief ../resources/asset-brief.example.json",
        description: "生成 pipeline/{slug}.json",
      },
      {
        title: "运行管线",
        command: "python gamefactory.py pipeline run --manifest ../pipeline/asset-brief.example.json --run-prompts --jobs 4",
        description: "并行执行；失败任务可 reset 后重跑",
      },
      {
        title: "查看状态",
        command: "python gamefactory.py pipeline status --manifest ../pipeline/asset-brief.example.json --json",
        description: "任务计数与 ready/failed 列表",
      },
    ],
  },
  {
    id: "godot",
    title: "Godot 与测试",
    commands: [
      {
        title: "组装工程",
        command: "python gamefactory.py godot assemble --assemble-file ../plans/godot_asset-brief.example.json",
        description: "导入素材到 games/{slug}",
      },
      {
        title: "玩法开发上下文",
        command: "python gamefactory.py godot dev-context --brief ../resources/asset-brief.example.json --project ../games/asset-brief.example",
        description: "生成 godot-developer 用的 dev handoff",
      },
      {
        title: "校验工程",
        command: "python gamefactory.py godot validate --project ../games/asset-brief.example",
        description: "检查 Godot 工程能否构建",
      },
      {
        title: "自动化试玩",
        command: "python gamefactory.py test run --project ../games/asset-brief.example --brief ../resources/asset-brief.example.json",
        description: "截图 + 视觉 QA（tester 角色）",
      },
    ],
  },
];
