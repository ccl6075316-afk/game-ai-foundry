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
        title: "创建配置",
        command: "设置 → 从示例创建 → 填写 API Key",
        description: "或手动复制 resources/config.example.json 到 ~/.gamefactory/config.json",
      },
      {
        title: "环境检测",
        command: "顶部工具栏 → 重新检测 → 安装缺失",
        description: "FFmpeg 可一键安装；Godot 需官方 zip 后在设置指定路径",
      },
    ],
  },
  {
    id: "workflow",
    title: "推荐流程",
    intro: "从零到可玩：策划 → 规划 → 生成 → 组装 → 开发玩法。",
    commands: [
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
    intro: "在仓库 cli/ 目录执行；GUI 工具栏可一键检测与安装。",
    commands: [
      {
        title: "检测全部准备项",
        command: "python gamefactory.py setup check --json",
        description: "FFmpeg、Godot、.NET、rembg 缺失项与安装方式",
      },
      {
        title: "自动安装 FFmpeg",
        command: "python gamefactory.py setup install ffmpeg",
        description: "下载到 ~/.gamefactory/toolchain/bin",
      },
      {
        title: "安装 rembg（可选）",
        command: "python gamefactory.py setup install rembg",
        description: "视频 AI 抠图；静态图仍可用色键",
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
        title: "校验 brief",
        command: "python gamefactory.py brief validate --brief ../resources/my-game-brief.json",
        description: "检查 JSON 契约与必填字段",
      },
      {
        title: "Brainstorm 导出",
        command: "python gamefactory.py brief brainstorm export -o ../resources/my-game-brief.json",
        description: "CLI 多轮策划后导出 frozen brief",
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
