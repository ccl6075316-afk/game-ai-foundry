/** GUI 工种 — 见 docs/HOST-CHAT-PRODUCT.md（AI 公司前台；可多实例） */

export type ChatAgentRole = "brief" | "product_host" | "programmer" | "it" | "advisor";

export const CHAT_AGENT_ROLES: ChatAgentRole[] = [
  "brief",
  "product_host",
  "programmer",
  "it",
  "advisor",
];

/** 工种展示名 — docs/HOST-CHAT-PRODUCT.md */
export const CHAT_AGENT_LABELS: Record<ChatAgentRole, string> = {
  brief: "策划",
  product_host: "项目经理",
  programmer: "程序员",
  it: "IT",
  advisor: "顾问",
};

/** 消息气泡头像字母（区别于菱形 Logo） */
export const CHAT_AGENT_AVATAR: Record<ChatAgentRole, string> = {
  brief: "策",
  product_host: "经",
  programmer: "程",
  it: "运",
  advisor: "顾",
};

export const CHAT_AGENT_HINTS: Record<ChatAgentRole, string> = {
  brief: "主对话：商量需求，明确说「落实 brief」后再定稿",
  product_host: "Agent：试玩反馈、分诊派工、推进任务（修改主入口）",
  programmer: "Agent：按任务改 Godot C#、跑 validate",
  it: "家庭运维：可读会话/文件 + shell；环境 / 草稿 / 流水线（信任本会话少弹卡）",
  advisor: "只答问题与给建议：做法选型、流程、缺资源；不改 brief / 不跑流水线",
};

export function roleHero(role: ChatAgentRole): { title: string; subtitle: string } {
  switch (role) {
    case "brief":
      return {
        title: "今天想做什么游戏？",
        subtitle:
          "和策划商量设计 → 保存 Brief → 生成北极星图定视觉锚 → 再找项目经理开流水线。气泡里的选项可以直接点。",
      };
    case "product_host":
      return {
        title: "有什么要改或推进？",
        subtitle: "Brief（含北极星）定好后，点「生成流水线」再「运行资产生成」；也可以直接说试玩问题和改动。",
      };
    case "programmer":
      return {
        title: "施工对话",
        subtitle: "消息会发给程序员执行器 CLI；按任务改代码与验收，协作靠本地文件。",
      };
    case "it":
      return {
        title: "家里哪台机器卡住了？",
        subtitle:
          "环境、草稿同步、看板与流水线都能管；默认可跑资产。改 Foundry 源码或大段玩法再回 Cursor。",
      };
    case "advisor":
      return {
        title: "想先问清楚再动手？",
        subtitle:
          "做法选型、制作流程、缺资源怎么办——只给建议，不改草稿。要落实设计找策划，修环境找 IT。",
      };
  }
}

export type RoleSuggestion = { label: string; desc: string; cmd: string };

export function roleSuggestions(role: ChatAgentRole): RoleSuggestion[] {
  if (role === "brief") {
    return [
      { label: "开始策划", desc: "多轮澄清需求", cmd: "/brief" },
      { label: "命令指南", desc: "GUI 指令速查", cmd: "/guide" },
      { label: "检测环境", desc: "doctor + 工具栏", cmd: "/doctor" },
    ];
  }
  if (role === "product_host") {
    return [
      { label: "生成流水线", desc: "用已导出的 Brief 排任务", cmd: "生成流水线" },
      { label: "运行资产生成", desc: "含文案生成并出图", cmd: "运行资产生成（含文案）" },
      { label: "改需求 Delta", desc: "增量改蓝图", cmd: "/delta 003-feature | 描述改动" },
      { label: "打开看板", desc: "看右侧任务列表", cmd: "打开看板" },
      { label: "打开 Godot", desc: "编辑器", cmd: "/godot" },
    ];
  }
  if (role === "it") {
    return [
      { label: "跑 doctor", desc: "环境与密钥", cmd: "帮我跑 doctor，用 JSON 看缺什么" },
      { label: "同步草稿", desc: "bind + 落盘", cmd: "把当前会话草稿同步到工程目录" },
      { label: "流水线诊断", desc: "pipeline diagnose", cmd: "对当前工程跑 pipeline diagnose" },
      { label: "跑资产生成", desc: "pipeline run", cmd: "对当前工程跑 pipeline run，jobs 用 2" },
      { label: "Pi 状态", desc: "内置执行器", cmd: "检查内置 Pi 是否就绪" },
      { label: "命令指南", desc: "CLI 速查", cmd: "/guide" },
    ];
  }
  if (role === "advisor") {
    return [
      { label: "动画选型", desc: "代码 vs 视频", cmd: "鱼竿弯曲、海面波浪，哪些用代码做、哪些适合生视频？" },
      { label: "缺资源怎么办", desc: "占位还是补资产", cmd: "写 demo 写到一半发现缺贴图/动画，应该停下来补还是先占位？" },
      { label: "文档分层", desc: "brief vs 数据表", cmd: "brief 该写多细？场景摆放和点击效果要不要等 demo 后再做数据表？" },
      { label: "命令指南", desc: "GUI 速查", cmd: "/guide" },
    ];
  }
  return [
    { label: "打开 Godot", desc: "查看工程", cmd: "/godot" },
    { label: "检测环境", desc: "Godot / .NET", cmd: "/doctor" },
    { label: "命令指南", desc: "CLI 速查", cmd: "/guide" },
  ];
}
