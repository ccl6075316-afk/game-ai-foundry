/** GUI 三种工种 — 见 docs/HOST-CHAT-PRODUCT.md（AI 公司前台；可多实例） */

export type ChatAgentRole = "brief" | "product_host" | "programmer";

export const CHAT_AGENT_ROLES: ChatAgentRole[] = ["brief", "product_host", "programmer"];

/** 工种展示名 — docs/HOST-CHAT-PRODUCT.md */
export const CHAT_AGENT_LABELS: Record<ChatAgentRole, string> = {
  brief: "策划",
  product_host: "项目经理",
  programmer: "程序员",
};

/** 消息气泡头像字母（区别于菱形 Logo） */
export const CHAT_AGENT_AVATAR: Record<ChatAgentRole, string> = {
  brief: "策",
  product_host: "经",
  programmer: "程",
};

export const CHAT_AGENT_HINTS: Record<ChatAgentRole, string> = {
  brief: "主对话：商量需求，明确说「落实 brief」后再定稿",
  product_host: "Agent：试玩反馈、分诊派工、推进任务（修改主入口）",
  programmer: "Agent：按任务改 Godot C#、跑 validate",
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
  return [
    { label: "打开 Godot", desc: "查看工程", cmd: "/godot" },
    { label: "检测环境", desc: "Godot / .NET", cmd: "/doctor" },
    { label: "命令指南", desc: "CLI 速查", cmd: "/guide" },
  ];
}
