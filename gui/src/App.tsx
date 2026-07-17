import { useCallback, useEffect, useRef, useState } from "react";
import type { PipelineStatus, PipelineTask } from "./vite-env.d";
import { ChatView } from "./components/ChatView";
import { ChatInput } from "./components/ChatInput";
import { ColleagueRoster } from "./components/ColleagueRoster";
import { BoardPanel } from "./components/BoardPanel";
import { SettingsPanel } from "./components/SettingsPanel";
import { ToolchainModal } from "./components/ToolchainModal";
import { EnvToolbar } from "./components/EnvToolbar";
import { EnvPanel } from "./components/EnvPanel";
import { GuidePanel } from "./components/GuidePanel";
import type { ToolchainReport } from "./settings/toolchain";
import type { ExecutorSetupReport, ExecutorId } from "./settings/executorsSetup";
import { autoInstallable } from "./settings/toolchain";
import type { DoctorReport } from "./vite-env.d";
import { newMessageId, parseChatCommand, parseRunFlags, type ChatAttachment, type ChatMessage } from "./chat/types";
import { extractMediaPaths, mergeAttachments } from "./chat/extractMediaPaths";
import {
  loadActiveBriefRel,
  parseDeltaCommand,
  parsePlanSubcommand,
  planTargetsFromBrief,
  productionPathFromBrief,
  progressPathFromBrief,
  saveActiveBriefRel,
} from "./chat/projectPaths";
import { roleHero, roleSuggestions, type ChatAgentRole } from "./chat/roles";
import {
  getActiveColleague,
  getActiveSession,
  listSessionsForInstance,
  loadSessionStore,
  saveSessionStore,
  setActiveInstance,
  setActiveSessionId,
  startNewSession,
  updateActiveMessages,
  updateSessionMessages,
  hireColleague,
  renameColleague,
  removeColleague,
  type ChatSessionStore,
} from "./chat/sessions";
type SidePanel = "board" | "settings" | "env" | "guide" | null;

function slugifyBriefName(raw: string): string {
  const t = raw.trim().toLowerCase();
  if (/[\u4e00-\u9fff]/.test(t)) {
    return `game-${Date.now().toString(36)}`;
  }
  const slug = t.replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  return slug || `game-${Date.now().toString(36)}`;
}

function parseBriefSubcommand(
  text: string,
): { action: "start" | "save" | "reset" | "status"; name?: string } | null {
  const parts = text.trim().split(/\s+/);
  if (parts[0]?.toLowerCase() !== "/brief") return null;
  const sub = (parts[1] || "start").toLowerCase();
  if (sub === "save" || sub === "export") {
    return { action: "save", name: parts.slice(2).join(" ").trim() || undefined };
  }
  if (sub === "reset") {
    return { action: "reset", name: parts.slice(2).join(" ").trim() || undefined };
  }
  if (sub === "status") return { action: "status" };
  return { action: "start", name: parts.slice(2).join(" ").trim() || undefined };
}

export default function App() {
  const [selectedManifest, setSelectedManifest] = useState("");
  const [activeBriefRel, setActiveBriefRel] = useState<string | null>(() => loadActiveBriefRel());
  const [tasks, setTasks] = useState<PipelineTask[]>([]);
  const [status, setStatus] = useState<PipelineStatus | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [chatStore, setChatStore] = useState<ChatSessionStore>(() => loadSessionStore());
  const [sidePanel, setSidePanel] = useState<SidePanel>(null);
  /** 正在等待回复的同事 instanceId（可并行；避免一人转圈三人一起 loading） */
  const [busyInstanceIds, setBusyInstanceIds] = useState<string[]>([]);
  const markBusy = useCallback((instanceId: string) => {
    setBusyInstanceIds((prev) => (prev.includes(instanceId) ? prev : [...prev, instanceId]));
  }, []);
  const clearBusy = useCallback((instanceId: string) => {
    setBusyInstanceIds((prev) => prev.filter((id) => id !== instanceId));
  }, []);
  const anyBusy = busyInstanceIds.length > 0;
  const [brainstormActive, setBrainstormActive] = useState(false);
  const [brainstormChoices, setBrainstormChoices] = useState<string[]>([]);
  const [brainstormReady, setBrainstormReady] = useState(false);
  const [draftTitle, setDraftTitle] = useState("");
  const [toolchainReport, setToolchainReport] = useState<ToolchainReport | null>(null);
  const [toolchainDismissed, setToolchainDismissed] = useState(false);
  const [toolchainInstalling, setToolchainInstalling] = useState<string | null>(null);
  const [toolchainLog, setToolchainLog] = useState<string[]>([]);
  const autoEnsureDone = useRef(false);
  const [executorSetup, setExecutorSetup] = useState<ExecutorSetupReport | null>(null);
  const [executorBusy, setExecutorBusy] = useState<string | null>(null);
  const [doctorReport, setDoctorReport] = useState<DoctorReport | null>(null);
  const [envScanning, setEnvScanning] = useState(false);
  const [openHandoffs, setOpenHandoffs] = useState<
    Array<{
      id?: string;
      path?: string;
      status?: string;
      triage?: string;
      title?: string;
      task_id?: string;
      target_instance_id?: string | null;
    }>
  >([]);
  const [agentActionChoices, setAgentActionChoices] = useState<string[]>([]);
  const pendingTargetProgrammer = useRef<string | null>(null);
  const pendingSafeActions = useRef<Map<string, string>>(new Map());

  const activeColleague = getActiveColleague(chatStore);
  const agentRole = activeColleague.roleKind;
  const activeSession = getActiveSession(chatStore);
  const messages = activeSession.messages;
  const chatBusy = busyInstanceIds.includes(activeColleague.id);
  const instanceSessions = listSessionsForInstance(chatStore, activeColleague.id);
  const heroBase = roleHero(agentRole);
  const hero = {
    title: heroBase.title,
    subtitle: `${activeColleague.displayName} — ${heroBase.subtitle}`,
  };
  const suggestions = roleSuggestions(agentRole);
  const handoffsForRoster = openHandoffs;

  const patchChatStore = useCallback((updater: (prev: ChatSessionStore) => ChatSessionStore) => {
    setChatStore((prev) => {
      const next = updater(prev);
      saveSessionStore(next);
      return next;
    });
  }, []);

  const setBrief = useCallback((briefRel: string) => {
    const normalized = briefRel.replace(/\\/g, "/");
    setActiveBriefRel(normalized);
    saveActiveBriefRel(normalized);
  }, []);

  const resolveBriefForPlan = useCallback(
    async (explicit?: string | null): Promise<string | null> => {
      if (explicit) return explicit.replace(/\\/g, "/");
      if (activeBriefRel) return activeBriefRel;
      const stored = loadActiveBriefRel();
      if (stored) return stored;
      const briefs = await window.gameFactory.listBriefs();
      return briefs[0]?.path || null;
    },
    [activeBriefRel],
  );

  const toggleSidePanel = (panel: Exclude<SidePanel, null>) => {
    setSidePanel((current) => (current === panel ? null : panel));
  };

  const appendAssistant = useCallback(
    (
      content: string,
      choices?: string[],
      attachments?: ChatAttachment[],
      target?: { instanceId: string; sessionId: string },
    ) => {
      patchChatStore((prev) => {
        const msg = {
          id: newMessageId(),
          role: "assistant" as const,
          content,
          timestamp: Date.now(),
          choices: choices?.length ? choices : undefined,
          attachments: attachments?.length ? attachments : undefined,
        };
        if (target) {
          return updateSessionMessages(prev, target.instanceId, target.sessionId, (msgs) => [
            ...msgs,
            msg,
          ]);
        }
        return updateActiveMessages(prev, (msgs) => [...msgs, msg]);
      });
      if (!target || target.instanceId === getActiveColleague(loadSessionStore()).id) {
        setBrainstormChoices(choices || []);
      }
    },
    [patchChatStore],
  );

  const applyBrainstormResult = useCallback(
    (
      data: {
        assistant_message?: string;
        choices?: string[];
        ready_to_export?: boolean;
        draft_brief?: { project?: { title?: string } };
      },
      target?: { instanceId: string; sessionId: string },
    ) => {
      if (!data.assistant_message) return;
      setBrainstormActive(true);
      appendAssistant(data.assistant_message, data.choices, undefined, target);
      setBrainstormReady(Boolean(data.ready_to_export));
      const title = data.draft_brief?.project?.title;
      if (title) setDraftTitle(String(title));
    },
    [appendAssistant],
  );

  const refreshBrainstormStatus = useCallback(async () => {
    if (!window.gameFactory?.hostChatStatus) return;
    const sid = getActiveSession(loadSessionStore()).id;
    const res = await window.gameFactory.hostChatStatus(sid);
    const data = res.data;
    if (data?.exists && (data.message_count || 0) > 0) {
      setBrainstormActive(true);
      setBrainstormReady(Boolean(data.ready_to_export));
      setBrainstormChoices(data.last_choices || []);
      if (data.title) setDraftTitle(data.title);
    }
  }, []);

  const append = useCallback(
    (
      role: ChatMessage["role"],
      content: string,
      attachments?: ChatAttachment[],
      target?: { instanceId: string; sessionId: string },
    ) => {
      patchChatStore((prev) => {
        const msg = {
          id: newMessageId(),
          role,
          content,
          timestamp: Date.now(),
          attachments: attachments?.length ? attachments : undefined,
        };
        if (target) {
          return updateSessionMessages(prev, target.instanceId, target.sessionId, (msgs) => [
            ...msgs,
            msg,
          ]);
        }
        return updateActiveMessages(prev, (msgs) => [...msgs, msg]);
      });
    },
    [patchChatStore],
  );

  const handleSelectColleague = useCallback(
    (instanceId: string) => {
      patchChatStore((prev) => setActiveInstance(prev, instanceId));
      setBrainstormChoices([]);
      setBrainstormReady(false);
      setAgentActionChoices([]);
    },
    [patchChatStore],
  );

  const refreshHandoffs = useCallback(async () => {
    if (!window.gameFactory?.handoffList) {
      setOpenHandoffs([]);
      return;
    }
    try {
      const res = await window.gameFactory.handoffList("open");
      const items = res.data?.handoffs || [];
      setOpenHandoffs(items);
    } catch {
      setOpenHandoffs([]);
    }
  }, []);

  const handleSwitchToProgrammer = useCallback(
    (instanceId?: string) => {
      const prog =
        (instanceId &&
          chatStore.roster.find((c) => c.id === instanceId && c.roleKind === "programmer")) ||
        chatStore.roster.find((c) => c.roleKind === "programmer");
      if (!prog) {
        append("assistant", "还没有程序员同事。请用「+ 雇佣」添加一位程序员。");
        return;
      }
      patchChatStore((prev) => setActiveInstance(prev, prog.id));
      setAgentActionChoices([]);
      setBrainstormChoices([]);
      void refreshHandoffs();
    },
    [chatStore.roster, patchChatStore, append, refreshHandoffs],
  );

  const handleHire = useCallback(
    (roleKind: ChatAgentRole) => {
      // Electron 无 window.prompt；先用默认名，再「改名」
      patchChatStore((prev) => hireColleague(prev, roleKind));
      setBrainstormActive(false);
      setBrainstormReady(false);
      setBrainstormChoices([]);
      setDraftTitle("");
    },
    [patchChatStore],
  );

  const handleRenameColleague = useCallback(
    (instanceId: string, displayName: string) => {
      patchChatStore((prev) => renameColleague(prev, instanceId, displayName));
    },
    [patchChatStore],
  );

  const handleRemoveColleague = useCallback(
    (instanceId: string) => {
      patchChatStore((prev) => removeColleague(prev, instanceId));
      setBrainstormActive(false);
      setBrainstormReady(false);
      setBrainstormChoices([]);
    },
    [patchChatStore],
  );

  const handleNewChat = useCallback(() => {
    patchChatStore((prev) => startNewSession(prev, prev.activeInstanceId));
    setBrainstormActive(false);
    setBrainstormReady(false);
    setBrainstormChoices([]);
    setDraftTitle("");
  }, [patchChatStore]);

  const handleSelectSession = useCallback(
    (sessionId: string) => {
      patchChatStore((prev) => setActiveSessionId(prev, prev.activeInstanceId, sessionId));
      setBrainstormChoices([]);
      setBrainstormReady(false);
      void (async () => {
        if (!window.gameFactory?.hostChatStatus) return;
        const res = await window.gameFactory.hostChatStatus(sessionId);
        const data = res.data;
        if (data?.exists && (data.message_count || 0) > 0) {
          setBrainstormActive(true);
          setBrainstormReady(Boolean(data.ready_to_export));
          setBrainstormChoices(data.last_choices || []);
          if (data.title) setDraftTitle(data.title);
        } else {
          setBrainstormActive(false);
          setDraftTitle("");
        }
      })();
    },
    [patchChatStore],
  );

  const handleBrainstormStart = async (seed?: string) => {
    const busyId = activeColleague.id;
    const sessionTarget = { instanceId: busyId, sessionId: getActiveSession(chatStore).id };
    markBusy(busyId);
    setBrainstormChoices([]);
    try {
      const res = await window.gameFactory.hostChatStart(sessionTarget.sessionId, seed);
      if (res.exitCode !== 0 || !res.data?.assistant_message) {
        throw new Error(res.stderr || res.stdout || "host-chat start failed");
      }
      applyBrainstormResult(res.data, sessionTarget);
    } catch (e) {
      appendAssistant(
        `Brief 对话启动失败：${e instanceof Error ? e.message : String(e)}\n\n请先在 **设置 → 在线服务 → 项目经理** 配置 API Key。`,
        undefined,
        undefined,
        sessionTarget,
      );
    } finally {
      clearBusy(busyId);
    }
  };

  const handleBrainstormTurn = async (message: string) => {
    const busyId = activeColleague.id;
    const sessionTarget = { instanceId: busyId, sessionId: getActiveSession(chatStore).id };
    markBusy(busyId);
    setBrainstormChoices([]);
    try {
      let res = await window.gameFactory.hostChatTurn(sessionTarget.sessionId, message);
      if (res.exitCode !== 0 && /Session not found/i.test(res.stderr || res.stdout || "")) {
        res = await window.gameFactory.hostChatStart(sessionTarget.sessionId, message);
      }
      if (res.exitCode !== 0 || !res.data?.assistant_message) {
        throw new Error(res.stderr || res.stdout || "host-chat turn failed");
      }
      applyBrainstormResult(res.data, sessionTarget);
    } catch (e) {
      appendAssistant(`回复失败：${e instanceof Error ? e.message : String(e)}`, undefined, undefined, sessionTarget);
    } finally {
      clearBusy(busyId);
    }
  };

  const handleBriefExport = async (nameHint?: string) => {
    const busyId = activeColleague.id;
    const sessionTarget = { instanceId: busyId, sessionId: getActiveSession(chatStore).id };
    markBusy(busyId);
    try {
      const slug = slugifyBriefName(nameHint || draftTitle || "my-game");
      const outputRel = `resources/${slug}-brief.json`;
      const res = await window.gameFactory.hostChatExport(sessionTarget.sessionId, outputRel);
      if (res.exitCode !== 0) {
        throw new Error(res.stderr || res.stdout || "export failed");
      }
      const path = res.data?.brief_path || outputRel;
      setBrief(outputRel);
      appendAssistant(
        `**Brief 已保存**\n\n\`${path}\`\n\n发送 \`/plan\` 生成流水线 manifest，再 \`/run\` 执行。`,
        undefined,
        undefined,
        sessionTarget,
      );
    } catch (e) {
      appendAssistant(`导出失败：${e instanceof Error ? e.message : String(e)}`, undefined, undefined, sessionTarget);
    } finally {
      clearBusy(busyId);
    }
  };

  const handleAgentTurn = async (message: string) => {
    if (agentRole !== "product_host" && agentRole !== "programmer") return;
    const target = {
      instanceId: activeColleague.id,
      sessionId: activeSession.id,
      role: agentRole,
      displayName: activeColleague.displayName,
    };
    markBusy(target.instanceId);
    setAgentActionChoices([]);
    const programmers = chatStore.roster.filter((c) => c.roleKind === "programmer");
    const defaultTarget =
      programmers.find((c) => c.id === target.instanceId)?.id || programmers[0]?.id;
    append("log", `「${target.displayName}」执行器运行中…`, undefined, target);
    try {
      if (!window.gameFactory?.agentTurn) {
        throw new Error("agentTurn IPC 不可用，请重启 GUI。");
      }
      const res = await window.gameFactory.agentTurn({
        role: target.role,
        sessionId: target.sessionId,
        message,
        brief: activeBriefRel || undefined,
        instanceId: target.instanceId,
        targetInstanceId: target.role === "product_host" ? defaultTarget : undefined,
        rosterJson:
          target.role === "product_host"
            ? JSON.stringify(
                programmers.map((c) => ({ id: c.id, display_name: c.displayName })),
              )
            : undefined,
      });
      const data = res.data;
      if (res.exitCode !== 0 || data?.ok === false) {
        const err =
          data?.error ||
          res.stderr ||
          res.stdout ||
          `agent turn failed (exit ${res.exitCode})`;
        throw new Error(err);
      }
      const reply = data?.assistant_message;
      if (!reply) {
        throw new Error(res.stderr || res.stdout || "executor 无回复");
      }
      const via = data.executor ? `\n\n—— via ${data.executor} CLI` : "";
      const dispatch = data.dispatch;
      let extra = "";
      const choices: string[] = [];
      pendingSafeActions.current = new Map();
      const queueActions = (actions: string[] | undefined) => {
        for (const raw of actions || []) {
          const line = String(raw || "").trim();
          if (!line || line.startsWith("#")) continue;
          const cmd = /^python\b/i.test(line) ? line : `python gamefactory.py ${line}`;
          const short = cmd.replace(/^python\s+gamefactory\.py\s+/i, "").slice(0, 48);
          const label = `执行 · ${short}`;
          pendingSafeActions.current.set(label, cmd);
          choices.push(label);
        }
      };
      if (target.role === "product_host" && dispatch?.handoff_path) {
        const tid = dispatch.target_instance_id;
        const targetName = tid
          ? chatStore.roster.find((c) => c.id === tid)?.displayName
          : undefined;
        extra =
          `\n\n**已派工**（文件总线）\n- handoff：\`${dispatch.handoff_id || dispatch.handoff_path}\`` +
          (tid ? `\n- 目标程序员：${targetName || tid}` : "") +
          `\n- 可点下方「切换到程序员」继续施工。`;
        choices.push("切换到程序员");
        if (tid) {
          pendingTargetProgrammer.current = tid;
        }
        queueActions(dispatch.next_actions);
      } else if (target.role === "product_host" && dispatch?.dispatch_to === "pipeline") {
        const actions = dispatch.next_actions || [];
        extra =
          `\n\n**资产/pipeline 分诊**` +
          (actions.length ? `\n建议命令：\n${actions.map((a) => `- \`${a}\``).join("\n")}` : "") +
          `\n\n可点下方「执行 · …」一键跑白名单命令。`;
        queueActions(actions);
      } else if (target.role === "programmer" && dispatch?.handoff_done) {
        extra =
          `\n\n**已关单** handoff \`${dispatch.handoff_done}\` → done` +
          (dispatch.task_done ? ` · task \`${dispatch.task_done}\` → done` : "");
        queueActions(dispatch.next_actions);
        if (activeBriefRel) {
          const proj = planTargetsFromBrief(activeBriefRel).godotProjectRel;
          const validateCmd = `python gamefactory.py godot validate --project ../${proj}`;
          const label = "执行 · godot validate";
          pendingSafeActions.current.set(label, validateCmd);
          choices.push(label);
        }
      } else if (target.role === "product_host") {
        queueActions(dispatch?.next_actions);
      }
      // Only surface action chips if user is still on this colleague
      if (getActiveColleague(loadSessionStore()).id === target.instanceId) {
        setAgentActionChoices(choices);
      }
      append(
        "assistant",
        `**${target.displayName}**\n\n${reply}${via}${extra}`,
        undefined,
        target,
      );
      await refreshHandoffs();
    } catch (e) {
      append(
        "assistant",
        `「${target.displayName}」回复失败：${e instanceof Error ? e.message : String(e)}\n\n请到 **环境** 面板确认执行器 CLI 已安装并登录（Hermes / Codex / Cursor Agent），并在设置里为项目经理/程序员选择执行器。`,
        undefined,
        target,
      );
    } finally {
      clearBusy(target.instanceId);
    }
  };

  const refreshManifest = useCallback(async (manifestRel: string) => {
    const res = await window.gameFactory.pipelineStatus(manifestRel);
    setStatus(res.status);
    setTasks(res.tasks || []);
    return res;
  }, []);

  const refreshToolchain = useCallback(async () => {
    if (!window.gameFactory?.toolchainCheck) return null;
    const res = await window.gameFactory.toolchainCheck();
    const report = res.data ?? null;
    if (report) setToolchainReport(report);
    return report;
  }, []);

  const refreshExecutorSetup = useCallback(async () => {
    if (!window.gameFactory?.executorStatus) return null;
    const res = await window.gameFactory.executorStatus();
    const report = res.data ?? null;
    if (report) setExecutorSetup(report);
    return report;
  }, []);

  const refreshEnv = useCallback(async () => {
    if (!window.gameFactory) return null;
    setEnvScanning(true);
    try {
      const docRes = await window.gameFactory.doctor();
      const doctor = docRes.data ?? null;
      if (doctor) setDoctorReport(doctor);
      const toolchain = await refreshToolchain();
      const executors = await refreshExecutorSetup();
      return { doctor, toolchain, executors };
    } finally {
      setEnvScanning(false);
    }
  }, [refreshToolchain, refreshExecutorSetup]);

  const loadInitial = useCallback(async () => {
    if (!window.gameFactory) return;
    await window.gameFactory.getPaths();
    await refreshEnv();
    await refreshHandoffs();

    const briefs = await window.gameFactory.listBriefs();
    const storedBrief = loadActiveBriefRel();
    const brief =
      storedBrief ||
      activeBriefRel ||
      briefs[0]?.path ||
      null;
    if (brief) setBrief(brief);

    const manifests = await window.gameFactory.listManifests();
    const preferredManifest = brief ? planTargetsFromBrief(brief).manifestRel : null;
    const manifest =
      (preferredManifest && manifests.find((x) => x.path === preferredManifest)?.path) ||
      manifests[0]?.path ||
      "";
    if (manifest) {
      setSelectedManifest(manifest);
      await refreshManifest(manifest);
    }
  }, [refreshManifest, activeBriefRel, setBrief, refreshEnv, refreshHandoffs]);

  const handleToolchainInstall = useCallback(
    async (componentId: string) => {
      if (!window.gameFactory?.toolchainInstall) return;
      setToolchainInstalling(componentId);
      setToolchainLog([]);
      try {
        const res = await window.gameFactory.toolchainInstall(componentId);
        if (res.stderr) setToolchainLog((prev) => [...prev, res.stderr]);
        if (res.stdout) setToolchainLog((prev) => [...prev, res.stdout]);
        if (res.exitCode !== 0) {
          appendAssistant(`安装 ${componentId} 失败，请查看日志或手动安装。`);
        }
        await refreshEnv();
      } catch (e) {
        appendAssistant(`安装失败：${e instanceof Error ? e.message : String(e)}`);
      } finally {
        setToolchainInstalling(null);
      }
    },
    [appendAssistant, refreshEnv],
  );

  const handleExecutorStep = useCallback(
    async (executorId: ExecutorId, stepId: string) => {
      if (!window.gameFactory?.executorStep) {
        appendAssistant("当前环境不支持执行器安装（executorStep 不可用），请用开发模式或完整 Release 包。");
        return;
      }
      const busyKey = `${executorId}:${stepId}`;
      setExecutorBusy(busyKey);
      setToolchainLog([]);
      try {
        const res = await window.gameFactory.executorStep(executorId, stepId);
        if (res.stderr) setToolchainLog((prev) => [...prev, res.stderr]);
        if (res.stdout) setToolchainLog((prev) => [...prev, res.stdout]);
        const data = res.data as
          | { ok?: boolean; message?: string; error?: string; status?: unknown }
          | undefined;
        if (data?.message) appendAssistant(data.message);
        if (res.exitCode !== 0 || data?.ok === false) {
          const err =
            data?.error ||
            res.stderr?.trim() ||
            `执行 ${executorId}/${stepId} 失败，请查看环境面板下方日志。`;
          appendAssistant(`❌ ${err}`);
          setToolchainLog((prev) => [...prev, err]);
        } else if (stepId === "login") {
          appendAssistant("已启动浏览器登录流程，完成后请点击「重新检测」确认状态。");
        } else if (!data?.message) {
          appendAssistant(`✅ ${executorId}/${stepId} 完成`);
        }
        if (data?.status) {
          setExecutorSetup((prev) =>
            prev
              ? {
                  ...prev,
                  executors: {
                    ...prev.executors,
                    [executorId]: data.status as ExecutorSetupReport["executors"][ExecutorId],
                  },
                }
              : prev,
          );
        }
        await refreshEnv();
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        appendAssistant(`❌ 执行失败：${msg}`);
        setToolchainLog((prev) => [...prev, msg]);
      } finally {
        setExecutorBusy(null);
      }
    },
    [appendAssistant, refreshEnv],
  );

  const handleToolchainInstallAll = useCallback(async () => {
    if (!toolchainReport) return;
    for (const item of autoInstallable(toolchainReport)) {
      await handleToolchainInstall(item.id);
    }
  }, [toolchainReport, handleToolchainInstall]);

  useEffect(() => {
    if (!toolchainReport || autoEnsureDone.current || toolchainInstalling) return;
    const requiredAuto = toolchainReport.components.filter(
      (c) => !c.available && c.required && (c.action === "auto" || c.action === "pip"),
    );
    if (!requiredAuto.length) return;
    autoEnsureDone.current = true;
    void (async () => {
      for (const item of requiredAuto) {
        await handleToolchainInstall(item.id);
      }
    })();
  }, [toolchainReport, toolchainInstalling, handleToolchainInstall]);

  useEffect(() => {
    void loadInitial()
      .then(() => refreshBrainstormStatus())
      .catch((e) =>
        append("system", `初始化失败：${e instanceof Error ? e.message : String(e)}`),
      );
    const offToolchain = window.gameFactory?.onToolchainLog?.(({ line }) => {
      setToolchainLog((prev) => [...prev.slice(-200), line]);
    });
    const off = window.gameFactory?.onPipelineLog(({ line }) => {
      setLogs((prev) => [...prev.slice(-200), line]);
      const found = extractMediaPaths(line);
      patchChatStore((store) =>
        updateActiveMessages(store, (prev) => {
          const last = prev[prev.length - 1];
          if (last?.role === "log") {
            return [
              ...prev.slice(0, -1),
              {
                ...last,
                content: `${last.content}\n${line}`.slice(-4000),
                attachments: mergeAttachments(last.attachments, found),
              },
            ];
          }
          return [
            ...prev,
            {
              id: newMessageId(),
              role: "log",
              content: line,
              timestamp: Date.now(),
              attachments: found.length ? found : undefined,
            },
          ];
        }),
      );
    });
    return () => {
      off?.();
      offToolchain?.();
    };
  }, [loadInitial, append, refreshBrainstormStatus]);

  const handleRun = async (runPrompts = false) => {
    if (!selectedManifest) {
      append("assistant", "还没有 pipeline manifest。请先完成 Brief 策划并发送 `/plan`。");
      return;
    }
    const busyId = activeColleague.id;
    markBusy(busyId);
    setLogs([]);
    try {
      append(
        "assistant",
        runPrompts
          ? "正在执行 `pipeline run --run-prompts`（含 prompt craft）…"
          : "正在执行 `pipeline run` …",
      );
      const res = await window.gameFactory.pipelineRun(selectedManifest, 4, runPrompts);
      if (res.exitCode !== 0) {
        append("assistant", `Pipeline 结束，exit ${res.exitCode}。\n${res.stderr || res.stdout}`);
      } else {
        append("assistant", "Pipeline 运行完成。可在看板查看任务状态。");
        try {
          const meta = await window.gameFactory.getManifestMeta(selectedManifest);
          const outputDir = meta?.output_dir;
          if (outputDir) {
            const gallery = await window.gameFactory.listOutputMedia(outputDir, 12);
            if (gallery.length > 0) {
              append("assistant", "**本次产出预览** — 点击缩略图打开原文件。", gallery);
            }
          }
        } catch {
          /* ignore gallery errors */
        }
      }
      await refreshManifest(selectedManifest);
      setSidePanel("board");
    } catch (e) {
      append("assistant", `运行失败：${e instanceof Error ? e.message : String(e)}`);
    } finally {
      clearBusy(busyId);
    }
  };

  const handleDoctor = async () => {
    const busyId = activeColleague.id;
    markBusy(busyId);
    try {
      const result = await refreshEnv();
      const d = result?.doctor;
      if (!d) {
        append("assistant", "doctor 无 JSON 输出。");
        return;
      }
      const caps = Object.entries(d.capabilities || {})
        .map(([k, ok]) => `${ok ? "✓" : "✗"} ${k}`)
        .join("\n");
      const tc = result?.toolchain;
      const missing = tc?.missing_required?.length
        ? `\n\n缺少必需工具：${tc.missing_required.join(", ")}`
        : "";
      append(
        "assistant",
        `**环境探测**\n\n${caps}\n\nOpenRouter: ${d.config.openrouter_key}\nSeedance: ${d.config.seedance_key}${missing}\n\n顶部工具栏可一键安装；侧栏「环境」查看详情。`,
      );
      setSidePanel("env");
    } finally {
      clearBusy(busyId);
    }
  };

  const handlePlan = async (explicitBrief?: string | null) => {
    const busyId = activeColleague.id;
    markBusy(busyId);
    try {
      const briefRel = await resolveBriefForPlan(explicitBrief);
      if (!briefRel) {
        append(
          "assistant",
          "还没有 brief。请先用 `/brief` 多轮策划并导出，或指定路径：`/plan resources/my-game-brief.json`",
        );
        return;
      }
      const targets = planTargetsFromBrief(briefRel);
      setBrief(briefRel);
      append(
        "assistant",
        `正在 pipeline plan …\n\nBrief: \`${targets.briefRel}\`\nManifest: \`${targets.manifestRel}\``,
      );
      const res = await window.gameFactory.pipelinePlan(targets);
      if (res.exitCode !== 0) throw new Error(res.stderr || "plan failed");
      setSelectedManifest(targets.manifestRel);
      await refreshManifest(targets.manifestRel);
      append(
        "assistant",
        `Manifest 已生成（\`${targets.manifestRel}\`）。发送 \`/run\` 执行，Godot 工程路径 \`${targets.godotProjectRel}\`。`,
      );
      setSidePanel("board");
    } catch (e) {
      append("assistant", `Plan 失败：${e instanceof Error ? e.message : String(e)}`);
    } finally {
      clearBusy(busyId);
    }
  };

  const handleOpenGodot = async () => {
    let projectRel = activeBriefRel ? planTargetsFromBrief(activeBriefRel).godotProjectRel : null;
    if (selectedManifest) {
      const meta = await window.gameFactory.getManifestMeta(selectedManifest);
      if (meta?.godot_project) projectRel = meta.godot_project;
    }
    if (!projectRel) {
      append("assistant", "还没有 Godot 工程路径。请先 `/plan` 生成 manifest。");
      return;
    }
    await window.gameFactory.openGodot(projectRel);
    append("assistant", `已尝试打开 \`${projectRel}\`。`);
  };

  const handleSafeAction = async (label: string) => {
    const cmd = pendingSafeActions.current.get(label);
    if (!cmd) {
      append("assistant", `找不到命令：${label}`);
      return;
    }
    const busyId = activeColleague.id;
    markBusy(busyId);
    append("user", label);
    append(
      "assistant",
      `正在执行白名单命令（日志会实时刷在下方）…\n\n\`${cmd}\``,
    );
    // Seed a log bubble so streaming lines attach
    append("log", "…");
    try {
      if (!window.gameFactory?.runSafeAction) {
        throw new Error("runSafeAction IPC 不可用，请重启 GUI。");
      }
      const res = await window.gameFactory.runSafeAction(cmd);
      const data = res.data;
      if (res.exitCode !== 0 || data?.ok === false) {
        throw new Error(data?.error || data?.stderr || res.stderr || `exit ${res.exitCode}`);
      }
      const out = (data?.stdout || res.stdout || "").trim();
      const err = (data?.stderr || "").trim();
      append(
        "assistant",
        `**已执行** \`${(data?.argv || []).join(" ") || cmd}\`\n\n` +
          (out ? `\`\`\`\n${out.slice(0, 4000)}\n\`\`\`` : "（无 stdout）") +
          (err ? `\n\nstderr:\n\`\`\`\n${err.slice(0, 1500)}\n\`\`\`` : ""),
      );
    } catch (e) {
      append("assistant", `执行失败：${e instanceof Error ? e.message : String(e)}`);
    } finally {
      clearBusy(busyId);
    }
  };

  const handleDelta = async (changeId: string, intent: string) => {
    if (!activeBriefRel) {
      append("assistant", "请先落实并导出 brief，再使用 `/delta`。");
      return;
    }
    const busyId = activeColleague.id;
    markBusy(busyId);
    try {
      if (!window.gameFactory?.productionDelta || !window.gameFactory?.productionApplyDelta) {
        throw new Error("production delta IPC 不可用，请重启 GUI。");
      }
      const productionRel = productionPathFromBrief(activeBriefRel);
      const progressRel = progressPathFromBrief(activeBriefRel);
      const deltaRel = `plans/changes/${changeId}.production-delta.json`;
      append(
        "assistant",
        `正在创建 Production Delta…\n\n- change: \`${changeId}\`\n- intent: ${intent}`,
      );
      const created = await window.gameFactory.productionDelta({
        changeId,
        intent,
        output: deltaRel,
      });
      if (created.exitCode !== 0) {
        throw new Error(created.stderr || created.stdout || "delta create failed");
      }
      const applied = await window.gameFactory.productionApplyDelta({
        delta: deltaRel,
        production: productionRel,
        progress: progressRel,
      });
      if (applied.exitCode !== 0) {
        throw new Error(
          applied.stderr ||
            applied.stdout ||
            `apply-delta failed — 若尚无 production，请先：python gamefactory.py production derive --brief ${activeBriefRel}`,
        );
      }
      const d = applied.data;
      append(
        "assistant",
        `**Delta 已合并**\n\n- delta：\`${deltaRel}\`\n- production：\`${productionRel}\`\n- 新增任务：\`${(d?.tasks_added || []).join(", ") || "—"}\`\n- progress 同步：\`${(d?.progress_tasks_added || []).join(", ") || "—"}\`\n\n可找项目经理派工，或让程序员按新 task 施工。`,
      );
      setAgentActionChoices(["切换到程序员"]);
    } catch (e) {
      append("assistant", `Delta 失败：${e instanceof Error ? e.message : String(e)}`);
    } finally {
      clearBusy(busyId);
    }
  };

  const handleSend = async (text: string) => {
    if (text.trim() === "切换到程序员") {
      const tid = pendingTargetProgrammer.current || undefined;
      pendingTargetProgrammer.current = null;
      handleSwitchToProgrammer(tid);
      return;
    }
    if (pendingSafeActions.current.has(text.trim())) {
      await handleSafeAction(text.trim());
      return;
    }
    const sendTarget = {
      instanceId: activeColleague.id,
      sessionId: activeSession.id,
    };
    append("user", text, undefined, sendTarget);

    const briefCmd = parseBriefSubcommand(text);
    if (briefCmd || text.trim().toLowerCase() === "/brief") {
      if (agentRole !== "brief") {
        append(
          "assistant",
          "Brief 策划请切换到 **策划** 同事。项目经理负责分诊派工；程序员负责写码验收。",
        );
        return;
      }
      const cmd = briefCmd || { action: "start" as const };
      if (cmd.action === "reset") {
        setBrainstormActive(false);
        setBrainstormReady(false);
        const busyId = activeColleague.id;
        markBusy(busyId);
        setBrainstormChoices([]);
        try {
          const sessionId = activeSession.id;
          const res = await window.gameFactory.hostChatReset(sessionId, cmd.name);
          if (res.exitCode !== 0 || !res.data?.assistant_message) {
            throw new Error(res.stderr || res.stdout || "host-chat reset failed");
          }
          applyBrainstormResult(res.data);
        } catch (e) {
          appendAssistant(`重置失败：${e instanceof Error ? e.message : String(e)}`);
        } finally {
          clearBusy(busyId);
        }
        return;
      }
      if (cmd.action === "save") {
        await handleBriefExport(cmd.name);
        return;
      }
      if (cmd.action === "status") {
        const res = await window.gameFactory.hostChatStatus(activeSession.id);
        const d = res.data;
        if (!d?.exists) {
          appendAssistant("当前没有进行中的 Brief 会话。发送 `/brief` 或描述游戏想法开始。");
          return;
        }
        appendAssistant(
          `**Brief 会话**\n\n标题：${d.title || "（未定）"}\n资产数：${d.asset_count ?? 0}\n轮次：${d.message_count ?? 0}\n模式：${d.mode || "chat"}\n可导出：${d.ready_to_export ? "是" : "否"}`,
          d.last_choices,
        );
        setBrainstormActive(true);
        setBrainstormReady(Boolean(d.ready_to_export));
        setBrainstormChoices(d.last_choices || []);
        return;
      }
      await handleBrainstormStart(cmd.name);
      return;
    }

    const cmd = parseChatCommand(text);
    if (cmd === "/doctor") {
      await handleDoctor();
      return;
    }
    if (cmd === "/plan") {
      const explicitBrief = parsePlanSubcommand(text);
      await handlePlan(explicitBrief);
      return;
    }
    if (cmd === "/run") {
      await handleRun(parseRunFlags(text).runPrompts);
      return;
    }
    if (cmd === "/board") {
      toggleSidePanel("board");
      append("assistant", "看板显示已切换 — 右侧查看 pipeline 任务 DAG。");
      return;
    }
    if (cmd === "/settings") {
      toggleSidePanel("settings");
      append("assistant", "设置面板已切换 — 右侧编辑 API Key 与 Godot 路径。");
      return;
    }
    if (cmd === "/env" || cmd === "/guide") {
      toggleSidePanel(cmd === "/env" ? "env" : "guide");
      append("assistant", cmd === "/env" ? "环境面板已打开 — 可检测并安装本机工具。" : "命令指南已打开 — 查看对话指令与 CLI 速查。");
      return;
    }
    if (cmd === "/godot") {
      await handleOpenGodot();
      return;
    }
    const delta = parseDeltaCommand(text);
    if (delta) {
      if (agentRole !== "product_host" && agentRole !== "brief") {
        append("assistant", "改需求请用 **项目经理** 或 **策划** 同事执行 `/delta`。");
        return;
      }
      await handleDelta(delta.changeId, delta.intent);
      return;
    }

    if (text.trim().startsWith("/")) {
      append(
        "assistant",
        `未知指令。可用：/brief /doctor /plan /run /board /settings /env /guide /godot /delta`,
      );
      return;
    }

    if (agentRole === "product_host" || agentRole === "programmer") {
      await handleAgentTurn(text);
      return;
    }

    if (brainstormActive) {
      await handleBrainstormTurn(text);
      return;
    }

    await handleBrainstormStart(text);
  };

  return (
    <div className="app chat-app">
      <header className="topbar">
        <div className="topbar__brand">
          <div className="topbar__logo">
            <svg viewBox="0 0 24 24" fill="none" width="18" height="18">
              <path
                d="M12 2L4 7v10l8 5 8-5V7l-8-5z"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <span className="topbar__title">Game AI Foundry</span>
        </div>
        <div className="topbar__actions">
          {status && (
            <span className={`badge ${status.done ? "badge--ok" : "badge--idle"}`}>
              {status.done ? "已完成" : "进行中"}
            </span>
          )}
          <button
            type="button"
            className={`btn btn--ghost ${sidePanel === "env" ? "btn--active" : ""}`}
            onClick={() => toggleSidePanel("env")}
          >
            环境
          </button>
          <button
            type="button"
            className={`btn btn--ghost ${sidePanel === "guide" ? "btn--active" : ""}`}
            onClick={() => toggleSidePanel("guide")}
          >
            指南
          </button>
          <button
            type="button"
            className={`btn btn--ghost ${sidePanel === "settings" ? "btn--active" : ""}`}
            onClick={() => toggleSidePanel("settings")}
          >
            <svg viewBox="0 0 24 24" fill="none" width="16" height="16">
              <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.5" />
              <path
                d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
              />
            </svg>
            设置
          </button>
          <button
            type="button"
            className={`btn btn--ghost ${sidePanel === "board" ? "btn--active" : ""}`}
            onClick={() => toggleSidePanel("board")}
          >
            <svg viewBox="0 0 24 24" fill="none" width="16" height="16">
              <rect x="3" y="3" width="7" height="7" rx="1.5" stroke="currentColor" strokeWidth="1.5" />
              <rect x="14" y="3" width="7" height="7" rx="1.5" stroke="currentColor" strokeWidth="1.5" />
              <rect x="3" y="14" width="7" height="7" rx="1.5" stroke="currentColor" strokeWidth="1.5" />
              <rect x="14" y="14" width="7" height="7" rx="1.5" stroke="currentColor" strokeWidth="1.5" />
            </svg>
            看板
          </button>
        </div>
      </header>

      <EnvToolbar
        toolchain={toolchainReport}
        executorSetup={executorSetup}
        doctor={doctorReport}
        scanning={envScanning}
        installing={Boolean(toolchainInstalling)}
        onScan={() => void refreshEnv()}
        onInstallAll={() => void handleToolchainInstallAll()}
        onOpenEnv={() => setSidePanel("env")}
        onOpenGuide={() => setSidePanel("guide")}
      />

      <div className={`chat-layout ${sidePanel ? "side-open" : ""}`}>
        <ColleagueRoster
          roster={chatStore.roster}
          activeInstanceId={activeColleague.id}
          sessions={instanceSessions}
          activeSessionId={activeSession.id}
          openHandoffs={handoffsForRoster}
          busyInstanceIds={busyInstanceIds}
          onSelectColleague={handleSelectColleague}
          onHire={handleHire}
          onRename={handleRenameColleague}
          onRemove={handleRemoveColleague}
          onNewChat={handleNewChat}
          onSelectSession={handleSelectSession}
          onSwitchToProgrammer={handleSwitchToProgrammer}
        />
        <section className="chat-column">
          <ChatView
            messages={messages}
            busy={chatBusy}
            agentRole={agentRole}
            agentLabel={activeColleague.displayName}
            onSuggestion={handleSend}
            heroTitle={hero.title}
            heroSubtitle={hero.subtitle}
            suggestions={suggestions}
          />
          <ChatInput
            disabled={chatBusy}
            choices={
              agentRole === "brief"
                ? brainstormChoices
                : agentActionChoices
            }
            readyToExport={agentRole === "brief" && brainstormReady}
            placeholder={
              agentRole === "brief"
                ? "描述游戏想法，或输入 /brief /doctor /plan …"
                : agentRole === "product_host"
                  ? "描述试玩问题或要推进的事（将发给项目经理执行器 CLI）…"
                  : "描述要改的代码/任务（将发给程序员执行器 CLI）…"
            }
            hint={
              agentRole === "brief"
                ? "Enter 发送 · 默认只聊天；说「落实成 brief」后才可导出 · `/brief save 名称`"
                : "Enter 发送 · 经 Hermes/Codex/Cursor Agent CLI 回信 · 会话按同事隔离"
            }
            onSend={handleSend}
            onChoice={handleSend}
            onExportBrief={agentRole === "brief" ? () => void handleBriefExport() : undefined}
          />
        </section>

        {sidePanel === "board" && (
          <BoardPanel
            manifest={selectedManifest}
            status={status}
            tasks={tasks}
            logs={logs}
            busy={anyBusy}
            onRefresh={() => refreshManifest(selectedManifest)}
            onRun={handleRun}
          />
        )}

        {sidePanel === "settings" && <SettingsPanel busy={anyBusy} />}

        {sidePanel === "env" && (
          <EnvPanel
            toolchain={toolchainReport}
            executorSetup={executorSetup}
            doctor={doctorReport}
            scanning={envScanning}
            installing={toolchainInstalling}
            executorBusy={executorBusy}
            installLog={toolchainLog}
            onRefresh={() => void refreshEnv()}
            onInstall={(id) => void handleToolchainInstall(id)}
            onInstallAll={() => void handleToolchainInstallAll()}
            onExecutorStep={(id, step) => void handleExecutorStep(id, step)}
            onOpenExternal={(url) => void window.gameFactory.openExternal(url)}
            onOpenSettings={() => setSidePanel("settings")}
          />
        )}

        {sidePanel === "guide" && <GuidePanel />}
      </div>

      {toolchainReport?.needs_attention && !toolchainDismissed && (
        <ToolchainModal
          report={toolchainReport}
          installing={toolchainInstalling}
          installLog={toolchainLog}
          onDismiss={() => setToolchainDismissed(true)}
          onInstall={(id) => void handleToolchainInstall(id)}
          onInstallAll={() => void handleToolchainInstallAll()}
          onOpenExternal={(url) => void window.gameFactory.openExternal(url)}
          onOpenSettings={() => {
            setToolchainDismissed(true);
            setSidePanel("settings");
          }}
        />
      )}
    </div>
  );
}
