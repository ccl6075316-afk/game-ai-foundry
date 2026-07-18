import { useCallback, useEffect, useRef, useState } from "react";
import type { ManifestMeta, PipelineStatus, PipelineTask } from "./vite-env.d";
import { ChatView } from "./components/ChatView";
import { ChatInput } from "./components/ChatInput";
import { ColleagueRoster } from "./components/ColleagueRoster";
import { BoardPanel } from "./components/BoardPanel";
import { DocsPreviewPanel } from "./components/DocsPreviewPanel";
import { SettingsPanel } from "./components/SettingsPanel";
import { ToolchainModal } from "./components/ToolchainModal";
import { EnvToolbar } from "./components/EnvToolbar";
import { EnvPanel } from "./components/EnvPanel";
import { GuidePanel } from "./components/GuidePanel";
import type { ToolchainReport } from "./settings/toolchain";
import type { ExecutorSetupReport, ExecutorId } from "./settings/executorsSetup";
import { autoInstallable } from "./settings/toolchain";
import {
  summarizeEnvHealth,
  formatEnvHealthChat,
  type EnvHealth,
} from "./settings/envHealth";
import type { DoctorReport } from "./vite-env.d";
import {
  newMessageId,
  parseChatCommand,
  parseRunFlags,
  type ChatAttachment,
  type ChatMessage,
  type HostChatDraftBrief,
  type HostChatDraftDocument,
  type HostChatStatus,
} from "./chat/types";
import { extractMediaPaths, mergeAttachments } from "./chat/extractMediaPaths";
import {
  briefExportRel,
  loadActiveBriefRel,
  parseDeltaCommand,
  parsePlanSubcommand,
  planTargetsFromBrief,
  productionPathFromBrief,
  progressPathFromBrief,
  saveActiveBriefRel,
} from "./chat/projectPaths";
import { roleHero, roleSuggestions, type ChatAgentRole } from "./chat/roles";
import { prepareAgentDisplay } from "./chat/agentReply";
import { mergeMessageChoices } from "./chat/inferChoices";
import { toRepoMediaRel } from "./chat/toRepoMediaRel";
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
type SidePanel = "board" | "docs" | "settings" | "env" | "guide" | null;

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
): { action: "start" | "save" | "reset" | "status" | "autofix"; name?: string; maxRounds?: number } | null {
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
  if (sub === "autofix" || sub === "fix") {
    const n = Number(parts[2]);
    return {
      action: "autofix",
      maxRounds: Number.isFinite(n) && n > 0 ? Math.min(12, Math.floor(n)) : undefined,
    };
  }
  return { action: "start", name: parts.slice(2).join(" ").trim() || undefined };
}

export default function App() {
  const [selectedManifest, setSelectedManifest] = useState("");
  const [activeBriefRel, setActiveBriefRel] = useState<string | null>(() => loadActiveBriefRel());
  /** brief.project.visual_reference is a real image path on disk */
  const [visualReferenceReady, setVisualReferenceReady] = useState(false);
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
  const [briefDraft, setBriefDraft] = useState<HostChatDraftBrief | null>(null);
  const [draftDocument, setDraftDocument] = useState<HostChatDraftDocument | null>(null);
  const [briefDraftStatus, setBriefDraftStatus] = useState<HostChatStatus | null>(null);
  const [toolchainReport, setToolchainReport] = useState<ToolchainReport | null>(null);
  const [toolchainDismissed, setToolchainDismissed] = useState(false);
  const [toolchainInstalling, setToolchainInstalling] = useState<string | null>(null);
  const [toolchainLog, setToolchainLog] = useState<string[]>([]);
  const autoEnsureDone = useRef(false);
  /** Soft-gate: warn once before pipeline run without visual_reference */
  const runWithoutVtWarned = useRef(false);
  const [executorSetup, setExecutorSetup] = useState<ExecutorSetupReport | null>(null);
  const [executorBusy, setExecutorBusy] = useState<string | null>(null);
  const [doctorReport, setDoctorReport] = useState<DoctorReport | null>(null);
  const [envHealth, setEnvHealth] = useState<EnvHealth | null>(null);
  const [envScanError, setEnvScanError] = useState<string | null>(null);
  const startupHealthPosted = useRef(false);
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
  const [busyHint, setBusyHint] = useState("");
  const instanceSessions = listSessionsForInstance(chatStore, activeColleague.id);

  useEffect(() => {
    if (!chatBusy) {
      setBusyHint("");
      return;
    }
    const started = Date.now();
    const tick = () => {
      const s = Math.floor((Date.now() - started) / 1000);
      const mm = String(Math.floor(s / 60)).padStart(1, "0");
      const ss = String(s % 60).padStart(2, "0");
      setBusyHint(
        `已等待 ${mm}:${ss} · 有计时跳动即正常；项目经理执行器常需 1–3 分钟，流水线任务会刷终端日志`,
      );
    };
    tick();
    const id = window.setInterval(tick, 1000);
    return () => window.clearInterval(id);
  }, [chatBusy]);
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

  const refreshVisualTarget = useCallback(async (briefRel?: string | null) => {
    const rel = (briefRel || activeBriefRel || "").replace(/\\/g, "/");
    if (!rel || !window.gameFactory?.visualTargetStatus) {
      setVisualReferenceReady(false);
      return false;
    }
    try {
      const st = await window.gameFactory.visualTargetStatus(rel);
      setVisualReferenceReady(Boolean(st.ready));
      return Boolean(st.ready);
    } catch {
      setVisualReferenceReady(false);
      return false;
    }
  }, [activeBriefRel]);

  const setBrief = useCallback((briefRel: string) => {
    const normalized = briefRel.replace(/\\/g, "/");
    setActiveBriefRel(normalized);
    saveActiveBriefRel(normalized);
    void refreshVisualTarget(normalized);
    // Canonicalize legacy resources/ ↔ cli/resources/ paths in the background
    void (async () => {
      if (!window.gameFactory?.resolveBriefRel) return;
      const r = await window.gameFactory.resolveBriefRel(normalized);
      if (r.exists && r.path && r.path !== normalized) {
        setActiveBriefRel(r.path);
        saveActiveBriefRel(r.path);
        void refreshVisualTarget(r.path);
      }
    })();
  }, [refreshVisualTarget]);

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
      const mergedChoices = mergeMessageChoices(choices, content);
      patchChatStore((prev) => {
        const msg = {
          id: newMessageId(),
          role: "assistant" as const,
          content,
          timestamp: Date.now(),
          choices: mergedChoices,
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
        setBrainstormChoices(mergedChoices || []);
      }
    },
    [patchChatStore],
  );

  const applyDraftFromPayload = useCallback(
    (
      data: {
        ready_to_export?: boolean;
        draft_brief?: HostChatDraftBrief | null;
        draft_document?: HostChatDraftDocument | null;
        title?: string;
        genre?: string;
        gameplay_loop?: string;
        asset_count?: number;
        assets?: HostChatStatus["assets"];
        gaps?: string[];
        contract_complete?: boolean;
        last_choices?: string[];
        mode?: string;
        message_count?: number;
        exists?: boolean;
        document_title?: string;
        has_document?: boolean;
      },
      opts?: { replace?: boolean },
    ) => {
      const replace = Boolean(opts?.replace);
      setBrainstormReady(Boolean(data.ready_to_export));
      if (data.draft_brief) {
        setBriefDraft(data.draft_brief);
        const title = data.draft_brief.project?.title || data.title;
        if (title) setDraftTitle(String(title));
      } else if (replace && data.draft_brief === null) {
        setBriefDraft(null);
      }
      if (data.draft_document) {
        setDraftDocument(data.draft_document);
      } else if (replace && (data.has_document === false || data.draft_document === null)) {
        setDraftDocument(null);
      }
      setBriefDraftStatus((prev) => {
        const nextDraft = data.draft_brief !== undefined ? data.draft_brief : replace ? null : prev?.draft_brief;
        const nextDoc =
          data.draft_document !== undefined
            ? data.draft_document
            : replace
              ? null
              : prev?.draft_document;
        // gaps: [] must clear old errors — never keep prev when server sent an array
        const nextGaps = Array.isArray(data.gaps) ? data.gaps : replace ? [] : prev?.gaps;
        return {
          exists: data.exists ?? (replace ? true : prev?.exists ?? true),
          ready_to_export: Boolean(data.ready_to_export),
          title:
            data.title ||
            (data.draft_brief?.project?.title as string | undefined) ||
            (replace ? "" : prev?.title || ""),
          genre:
            data.genre ||
            (data.draft_brief?.project?.genre as string | undefined) ||
            (replace ? "" : prev?.genre || ""),
          gameplay_loop:
            data.gameplay_loop ||
            (data.draft_brief?.project?.gameplay_loop as string | undefined) ||
            (replace ? "" : prev?.gameplay_loop || ""),
          asset_count:
            data.asset_count ??
            (Array.isArray(data.draft_brief?.assets)
              ? data.draft_brief!.assets!.length
              : replace
                ? 0
                : prev?.asset_count),
          assets: data.assets ?? (replace ? [] : prev?.assets),
          draft_brief: nextDraft ?? undefined,
          draft_document: nextDoc ?? undefined,
          document_title: data.document_title ?? (replace ? "" : prev?.document_title),
          has_document: data.has_document ?? (replace ? Boolean(nextDoc) : prev?.has_document),
          gaps: nextGaps,
          contract_complete: data.contract_complete,
          last_choices: data.last_choices ?? (replace ? [] : prev?.last_choices),
          mode: data.mode ?? (replace ? "chat" : prev?.mode),
          message_count: data.message_count ?? (replace ? 0 : prev?.message_count),
        };
      });
    },
    [],
  );

  const applyBrainstormResult = useCallback(
    (
      data: {
        assistant_message?: string;
        choices?: string[];
        ready_to_export?: boolean;
        draft_brief?: HostChatDraftBrief | null;
        draft_document?: HostChatDraftDocument | null;
        gaps?: string[];
      },
      target?: { instanceId: string; sessionId: string },
    ) => {
      if (!data.assistant_message) return;
      setBrainstormActive(true);
      appendAssistant(data.assistant_message, data.choices, undefined, target);
      applyDraftFromPayload(data);
    },
    [appendAssistant, applyDraftFromPayload],
  );

  const refreshBrainstormStatus = useCallback(async () => {
    if (!window.gameFactory?.hostChatStatus) return;
    const sid = getActiveSession(loadSessionStore()).id;
    const res = await window.gameFactory.hostChatStatus(sid);
    const data = res.data;
    if (data?.exists && (data.message_count || 0) > 0) {
      setBrainstormActive(true);
      // Don't wipe chips if status has no last_choices (message bubbles keep theirs)
      if (Array.isArray(data.last_choices) && data.last_choices.length > 0) {
        setBrainstormChoices(data.last_choices);
      }
      // Full replace so cleared gaps / updated draft are not stuck behind React merge
      applyDraftFromPayload(
        {
          ...data,
          draft_brief: data.draft_brief ?? null,
          draft_document: data.draft_document ?? null,
          gaps: Array.isArray(data.gaps) ? data.gaps : [],
        },
        { replace: true },
      );
      setBriefDraft(data.draft_brief ?? null);
      setDraftDocument(data.draft_document ?? null);
      if (data.title) setDraftTitle(data.title);
    } else {
      setBriefDraft(null);
      setDraftDocument(null);
      setBriefDraftStatus(null);
    }
  }, [applyDraftFromPayload]);

  const append = useCallback(
    (
      role: ChatMessage["role"],
      content: string,
      attachments?: ChatAttachment[],
      target?: { instanceId: string; sessionId: string },
      choices?: string[],
    ) => {
      const merged =
        role === "assistant" ? mergeMessageChoices(choices, content) : choices?.length ? choices : undefined;
      patchChatStore((prev) => {
        const msg = {
          id: newMessageId(),
          role,
          content,
          timestamp: Date.now(),
          attachments: attachments?.length ? attachments : undefined,
          choices: merged,
        };
        if (target) {
          return updateSessionMessages(prev, target.instanceId, target.sessionId, (msgs) => [
            ...msgs,
            msg,
          ]);
        }
        return updateActiveMessages(prev, (msgs) => [...msgs, msg]);
      });
      if (
        merged?.length &&
        (!target || target.instanceId === getActiveColleague(loadSessionStore()).id)
      ) {
        if (getActiveColleague(loadSessionStore()).roleKind === "brief") {
          setBrainstormChoices(merged);
        } else {
          setAgentActionChoices(merged);
        }
      }
    },
    [patchChatStore],
  );

  const handleSelectColleague = useCallback(
    (instanceId: string) => {
      patchChatStore((prev) => setActiveInstance(prev, instanceId));
      setBrainstormChoices([]);
      setBrainstormReady(false);
      setBriefDraft(null);
      setDraftDocument(null);
      setBriefDraftStatus(null);
      const next = loadSessionStore();
      const colleague = next.roster.find((c) => c.id === instanceId);
      if (colleague?.roleKind === "product_host") {
        setAgentActionChoices(["生成流水线", "运行资产生成（含文案）", "打开看板"]);
      } else {
        setAgentActionChoices([]);
      }
      if (colleague?.roleKind === "brief") {
        void refreshBrainstormStatus();
      }
    },
    [patchChatStore, refreshBrainstormStatus],
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
    setBriefDraft(null);
    setDraftDocument(null);
    setBriefDraftStatus(null);
  }, [patchChatStore]);

  const handleSelectSession = useCallback(
    (sessionId: string) => {
      patchChatStore((prev) => setActiveSessionId(prev, prev.activeInstanceId, sessionId));
      setBrainstormChoices([]);
      setBrainstormReady(false);
      setBriefDraft(null);
      setDraftDocument(null);
      setBriefDraftStatus(null);
      void (async () => {
        if (!window.gameFactory?.hostChatStatus) return;
        const res = await window.gameFactory.hostChatStatus(sessionId);
        const data = res.data;
        if (data?.exists && (data.message_count || 0) > 0) {
          setBrainstormActive(true);
          setBrainstormChoices(data.last_choices || []);
          applyDraftFromPayload(data);
          if (data.draft_brief) setBriefDraft(data.draft_brief);
          if (data.draft_document) setDraftDocument(data.draft_document);
        } else {
          setBrainstormActive(false);
          setDraftTitle("");
        }
      })();
    },
    [patchChatStore, applyDraftFromPayload],
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
      const data = res.data;
      if (res.exitCode !== 0 || !data?.assistant_message) {
        const detail = (res.stderr || res.stdout || "").trim();
        const short =
          detail.length > 1200 ? `${detail.slice(0, 1200)}\n…` : detail || "host-chat turn failed";
        throw new Error(short);
      }
      applyBrainstormResult(data, sessionTarget);
      void refreshBrainstormStatus();
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
      const outputRel = briefExportRel(slug);
      const res = await window.gameFactory.hostChatExport(sessionTarget.sessionId, outputRel);
      if (res.exitCode !== 0) {
        throw new Error(res.stderr || res.stdout || "export failed");
      }
      const briefRel = res.data?.brief_rel || outputRel;
      setBrief(briefRel);
      appendAssistant(
        `**Brief 已保存**（工程目录隔离）\n\n` +
          `- Brief：\`${briefRel}\`\n` +
          `- 工程根：\`projects/${slug}/\`（流水线 / 资产 / Godot 都会进这个目录）\n\n` +
          `下一步先在本对话定 **北极星图**（整屏风格锚），再交给项目经理跑流水线。`,
        ["生成北极星图", "切换到项目经理", "切换到项目经理并生成流水线"],
        undefined,
        sessionTarget,
      );
    } catch (e) {
      appendAssistant(`导出失败：${e instanceof Error ? e.message : String(e)}`, undefined, undefined, sessionTarget);
    } finally {
      clearBusy(busyId);
    }
  };

  const handleBriefAutofix = async (maxRounds = 5) => {
    if (!window.gameFactory?.hostChatAutofix) {
      appendAssistant("当前 GUI 不支持自动修 brief，请重启 Foundry。");
      return;
    }
    const busyId = activeColleague.id;
    const sessionTarget = { instanceId: busyId, sessionId: getActiveSession(chatStore).id };
    markBusy(busyId);
    append(
      "log",
      `自动修 brief：读取校验错误并循环修复（最多 ${maxRounds} 轮）…`,
      undefined,
      sessionTarget,
    );
    try {
      const res = await window.gameFactory.hostChatAutofix(sessionTarget.sessionId, maxRounds);
      const data = res.data;
      if (!data) {
        throw new Error(res.stderr || res.stdout || "autofix failed");
      }
      for (const round of data.rounds || []) {
        if (round.assistant_message) {
          const n = round.round ?? "?";
          const before = round.gap_count_before ?? "?";
          const after = round.gap_count_after ?? "?";
          appendAssistant(
            "**自动修 · 第 " +
              n +
              " 轮**（错误 " +
              before +
              " -> " +
              after +
              "）\n\n" +
              round.assistant_message,
            undefined,
            undefined,
            sessionTarget,
          );
        }
      }
      applyDraftFromPayload(
        {
          ...data,
          draft_brief: data.draft_brief ?? null,
          gaps: Array.isArray(data.gaps) ? data.gaps : [],
          ready_to_export: Boolean(data.ready_to_export),
        },
        { replace: true },
      );
      if (data.draft_brief) setBriefDraft(data.draft_brief);
      setBrainstormReady(Boolean(data.ready_to_export));
      const left = data.gaps?.length ?? 0;
      if (data.ok && left === 0) {
        appendAssistant(
          `**自动修完成**：校验已通过（用了 ${data.rounds_run ?? 0} 轮）。可点「保存 Brief」或 \`/brief save\`。`,
          data.ready_to_export ? ["保存 Brief"] : undefined,
          undefined,
          sessionTarget,
        );
      } else {
        const why =
          data.reason === "stuck"
            ? "连续多轮错误未变化，已停止"
            : data.reason === "max_rounds"
              ? `已达上限 ${data.max_rounds ?? maxRounds} 轮`
              : data.reason || "未全部通过";
        appendAssistant(
          `**自动修未完成**（${why}）。仍剩 ${left} 条错误——见右侧「文档」侧栏，可再点「自动修」或 \`/brief autofix ${maxRounds}\`。`,
          undefined,
          undefined,
          sessionTarget,
        );
      }
      void refreshBrainstormStatus();
    } catch (e) {
      appendAssistant(
        `自动修失败：${e instanceof Error ? e.message : String(e)}`,
        undefined,
        undefined,
        sessionTarget,
      );
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
    append(
      "log",
      `「${target.displayName}」执行器运行中…\n（右侧可开「看板」；下方会显示等待秒数。Hermes 常需 1–3 分钟才回完整答复。）`,
      undefined,
      target,
    );
    const agentStartedAt = Date.now();
    const heartbeat = window.setInterval(() => {
      const secs = Math.floor((Date.now() - agentStartedAt) / 1000);
      patchChatStore((store) =>
        updateSessionMessages(store, target.instanceId, target.sessionId, (prev) => {
          const last = prev[prev.length - 1];
          if (last?.role !== "log") return prev;
          const base =
            last.content.split("\n")[0] || `「${target.displayName}」执行器运行中…`;
          return [
            ...prev.slice(0, -1),
            {
              ...last,
              content: `${base}\n…仍在运行 ${secs}s（计时跳动即正常；Hermes 常需 1–3 分钟）`,
            },
          ];
        }),
      );
    }, 4000);
    try {
      if (!window.gameFactory?.agentTurn) {
        throw new Error("agentTurn IPC 不可用，请重启 GUI。");
      }
      const res = await window.gameFactory.agentTurn({
        role: target.role,
        sessionId: target.sessionId,
        message,
        brief: activeBriefRel || undefined,
        progress: activeBriefRel ? progressPathFromBrief(activeBriefRel) : undefined,
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
      const rawReply = (data?.assistant_message || "").trim();
      if (!rawReply) {
        throw new Error(res.stderr || res.stdout || "executor 无回复");
      }
      const prepared = prepareAgentDisplay(rawReply);
      const reply = prepared.display;
      const via = data?.executor ? `\n\n—— via ${data.executor} CLI` : "";
      const dispatch = data?.dispatch;
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
      if (prepared.weak && target.role === "product_host") {
        extra =
          prepared.reason === "config_noise"
            ? "\n\n请改用下方按钮推进项目（不要依赖这次 Agent 输出）："
            : "\n\n**执行器没有给出可用下一步。** 直接点下方按钮：";
        choices.push("生成流水线", "运行资产生成（含文案）", "打开看板");
      } else if (target.role === "product_host" && dispatch?.handoff_path) {
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
        if (!choices.some((c) => c.startsWith("生成流水线"))) {
          choices.push("生成流水线", "运行资产生成（含文案）");
        }
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
        for (const g of dispatch?.gui_hints || []) {
          const label = String(g || "").trim();
          if (label && !choices.includes(label)) choices.push(label);
        }
        if (!choices.some((c) => c.includes("生成流水线"))) {
          choices.push("生成流水线", "运行资产生成（含文案）", "打开看板");
        }
      }
      append(
        "assistant",
        `**${target.displayName}**\n\n${reply}${via}${extra}`,
        undefined,
        target,
        choices,
      );
      await refreshHandoffs();
    } catch (e) {
      append(
        "assistant",
        `「${target.displayName}」回复失败：${e instanceof Error ? e.message : String(e)}\n\n请到 **环境** 面板确认执行器 CLI 已安装并登录（Hermes / Codex / Cursor Agent），并在设置里为项目经理/程序员选择执行器。`,
        undefined,
        target,
        target.role === "product_host"
          ? ["生成流水线", "运行资产生成（含文案）", "打开看板"]
          : undefined,
      );
    } finally {
      window.clearInterval(heartbeat);
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
    setEnvScanError(null);
    try {
      const docRes = await window.gameFactory.doctor();
      const doctor = docRes.data ?? null;
      if (doctor) setDoctorReport(doctor);
      else setDoctorReport(null);

      const tcRes = window.gameFactory.toolchainCheck
        ? await window.gameFactory.toolchainCheck()
        : null;
      const toolchain = tcRes?.data ?? null;
      if (toolchain) setToolchainReport(toolchain);

      const executors = await refreshExecutorSetup();

      const health = summarizeEnvHealth({
        doctor,
        doctorExitCode: docRes.exitCode,
        doctorStderr: docRes.stderr,
        doctorStdout: docRes.stdout,
        toolchain,
        toolchainExitCode: tcRes?.exitCode ?? null,
        toolchainStderr: tcRes?.stderr,
        toolchainStdout: tcRes?.stdout,
        executors,
      });
      setEnvHealth(health);

      if (!doctor && docRes.exitCode !== 0) {
        setEnvScanError(
          (docRes.stderr || docRes.stdout || `doctor exit ${docRes.exitCode}`).slice(0, 500),
        );
      } else if (!toolchain && tcRes && tcRes.exitCode !== 0) {
        setEnvScanError(
          (tcRes.stderr || tcRes.stdout || `setup check exit ${tcRes.exitCode}`).slice(0, 500),
        );
      }

      return { doctor, toolchain, executors, health };
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setEnvScanError(msg);
      const health = summarizeEnvHealth({
        doctor: null,
        doctorStderr: msg,
        toolchain: null,
        toolchainStderr: msg,
      });
      setEnvHealth(health);
      return { doctor: null, toolchain: null, executors: null, health };
    } finally {
      setEnvScanning(false);
    }
  }, [refreshExecutorSetup]);

  const loadInitial = useCallback(async () => {
    if (!window.gameFactory) return;
    await window.gameFactory.getPaths();
    const env = await refreshEnv();
    await refreshHandoffs();

    const briefs = await window.gameFactory.listBriefs();
    const storedBrief = loadActiveBriefRel();
    const brief =
      storedBrief ||
      activeBriefRel ||
      briefs[0]?.path ||
      null;
    if (brief) setBrief(brief);

    const preferredManifest = brief ? planTargetsFromBrief(brief).manifestRel : null;
    const byBrief =
      brief && window.gameFactory.findManifestForBrief
        ? await window.gameFactory.findManifestForBrief(brief)
        : null;
    const manifests = await window.gameFactory.listManifests();
    const manifest =
      byBrief?.path ||
      (preferredManifest && manifests.find((x) => x.path === preferredManifest)?.path) ||
      manifests[0]?.path ||
      "";
    if (manifest) {
      setSelectedManifest(manifest);
      await refreshManifest(manifest);
    }
    if (brief) await refreshVisualTarget(brief);

    // Post clear health report once so end-users / supporters see failures
    if (!startupHealthPosted.current && env?.health) {
      startupHealthPosted.current = true;
      if (!env.health.ok || env.health.issues.length > 0) {
        append(
          "assistant",
          formatEnvHealthChat(env.health),
          undefined,
          undefined,
          env.health.ok ? undefined : ["打开环境", "打开设置"],
        );
        if (!env.health.ok) {
          setToolchainDismissed(false);
          setSidePanel("env");
        }
      }
    }
  }, [refreshManifest, activeBriefRel, setBrief, refreshEnv, refreshHandoffs, refreshVisualTarget, append]);

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
      append(
        "assistant",
        "还没有流水线。请先在 **策划** 导出 Brief，再切到 **项目经理** 点「生成流水线」。",
      );
      return;
    }
    if (!visualReferenceReady && !runWithoutVtWarned.current) {
      runWithoutVtWarned.current = true;
      append(
        "assistant",
        "尚未选定 **北极星图**（`visual_reference` 图片路径）。建议先点 **② 北极星图** 生成并选用，风格才容易一致。\n\n仍要直接跑资产？再点一次「运行资产生成」。",
        undefined,
        undefined,
        ["北极星图", "运行资产生成（含文案）"],
      );
      return;
    }
    const busyId = activeColleague.id;
    markBusy(busyId);
    setLogs([]);
    setSidePanel("board");
    const poll = window.setInterval(() => {
      void refreshManifest(selectedManifest);
    }, 6000);
    try {
      append(
        "assistant",
        (runPrompts
          ? "正在执行流水线（含文案生成）…\n"
          : "正在执行流水线…\n") +
          "已完成的任务会跳过，只跑 pending；终端日志与右侧看板会持续更新。失败任务需 reset 后再续跑。",
        undefined,
        undefined,
        ["打开看板"],
      );
      append("log", "pipeline run 开始…");
      const res = await window.gameFactory.pipelineRun(selectedManifest, 4, runPrompts);
      if (res.exitCode !== 0) {
        append(
          "assistant",
          `Pipeline 暂停/结束（exit ${res.exitCode}）。\n` +
            `已完成的任务会保留；修好后点「运行资产生成」会继续跑还差的 pending。\n` +
            `若某任务 failed，需先 reset 该 task 再跑。\n\n${(res.stderr || res.stdout || "").slice(0, 1500)}`,
          undefined,
          undefined,
          ["运行资产生成（含文案）", "运行资产生成", "打开看板"],
        );
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
      window.clearInterval(poll);
      clearBusy(busyId);
    }
  };

  const handleDoctor = async () => {
    const busyId = activeColleague.id;
    markBusy(busyId);
    try {
      const result = await refreshEnv();
      const health = result?.health;
      if (!health) {
        append(
          "assistant",
          `**环境检测失败**\n\n${envScanError || "无输出"}\n\n请把以上原文发给支持。`,
          undefined,
          undefined,
          ["打开环境", "打开设置"],
        );
        setSidePanel("env");
        return;
      }
      append(
        "assistant",
        formatEnvHealthChat(health),
        undefined,
        undefined,
        health.ok ? ["打开环境"] : ["打开环境", "打开设置"],
      );
      setSidePanel("env");
      if (!health.ok) setToolchainDismissed(false);
    } finally {
      clearBusy(busyId);
    }
  };

  const summarizeManifest = (manifestRel: string, meta: ManifestMeta | null | undefined) => {
    const counts = meta?.counts || status?.counts || {};
    const total = meta?.task_count ?? tasks.length;
    const parts = Object.entries(counts)
      .filter(([, n]) => Number(n) > 0)
      .map(([k, n]) => `${k} ${n}`)
      .join(" · ");
    const title = meta?.project_title ? `「${meta.project_title}」` : "";
    return (
      `✓ **流水线任务清单已就绪** ${title}\n\n` +
      `- 文件：\`${manifestRel}\`\n` +
      `- 任务：${total || "?"} 个` +
      (parts ? `（${parts}）` : "") +
      `\n\n右侧看板已打开。下一步点 **② 北极星图**（生成并选用整屏参考），再点 **③ 运行资产生成**。`
    );
  };

  const handleVisualTargetGenerate = async () => {
    const briefRel = activeBriefRel;
    if (!briefRel) {
      append(
        "assistant",
        "还没有 Brief。请先在 **策划** 导出，再点「北极星图」。",
      );
      return;
    }
    if (!window.gameFactory?.visualTargetGenerate) {
      append("assistant", "当前客户端不支持北极星图，请重启 Electron 后重试。");
      return;
    }
    // Block clearly when image API is missing — otherwise users only see opaque exit codes
    const imageOk = doctorReport?.capabilities?.image_api || doctorReport?.config?.openrouter_key === "set";
    if (envHealth && !envHealth.ok) {
      const apiIssue = envHealth.blocking.find((i) => i.id === "image-api-key" || i.id === "config-missing");
      if (apiIssue || !imageOk) {
        append(
          "assistant",
          formatEnvHealthChat(envHealth) +
            "\n\n**北极星图需要先配置图像 API。** 修好后点「重新检测」，再生成北极星。",
          undefined,
          undefined,
          ["打开设置", "打开环境"],
        );
        setSidePanel("settings");
        return;
      }
    } else if (!imageOk) {
      append(
        "assistant",
        "**无法生成北极星图：图像 API Key 未配置或检测未通过。**\n\n请打开设置填入 Key，再点顶部「重新检测」。把检测失败的原文发给支持即可。",
        undefined,
        undefined,
        ["打开设置", "打开环境"],
      );
      setSidePanel("settings");
      return;
    }
    const busyId = activeColleague.id;
    markBusy(busyId);
    setLogs([]);
    try {
      let brief = briefRel;
      if (window.gameFactory.resolveBriefRel) {
        const r = await window.gameFactory.resolveBriefRel(briefRel);
        if (!r.exists) {
          append(
            "assistant",
            `找不到 Brief 文件：\`${briefRel}\`\n请确认已导出，或切回策划重新保存。`,
          );
          return;
        }
        if (r.path !== briefRel) {
          setBrief(r.path);
          brief = r.path;
        }
      }
      append(
        "assistant",
        "正在生成北极星候选图（整屏玩法预览）…\n完成后点「选用北极星 a/b/c」。",
      );
      append("log", "visual-target generate 开始…");
      const res = await window.gameFactory.visualTargetGenerate(brief, 3);
      if (res.exitCode !== 0) {
        append(
          "assistant",
          `北极星生成失败（exit ${res.exitCode}）。\n\n${(res.stderr || res.stdout || "").slice(0, 1500)}`,
          undefined,
          undefined,
          ["北极星图", "打开看板"],
        );
        return;
      }
      const data = res.data || {};
      const cands = Array.isArray(data.candidates) ? data.candidates : [];
      const gallery = cands
        .map((c) => {
          const absOrRel = String(c.path || "");
          if (!absOrRel) return null;
          const rel = toRepoMediaRel(absOrRel);
          if (!rel) return null;
          return {
            path: rel,
            kind: "image" as const,
            label: `[${c.id}] ${c.label || ""}`.trim(),
          };
        })
        .filter((x): x is NonNullable<typeof x> => Boolean(x));
      const pickChoices = [
        ...cands
          .map((c) => String(c.id || "").trim().toLowerCase())
          .filter(Boolean)
          .map((id) => `选用北极星 ${id}`),
        "都不满意，换风格",
      ];
      append(
        "assistant",
        gallery.length
          ? "北极星候选已生成。点缩略图可看大图；满意就「选用北极星 …」。都不满意就点「都不满意，换风格」，跟策划改 `art_direction` 后再生成。"
          : "北极星流程已结束（可能无预览路径）。可「生成北极星图」重试，或「都不满意，换风格」。",
        gallery.length ? gallery : undefined,
        undefined,
        pickChoices,
      );
      await refreshVisualTarget(briefRel);
    } catch (e) {
      append(
        "assistant",
        `北极星生成异常：${e instanceof Error ? e.message : String(e)}`,
      );
    } finally {
      clearBusy(busyId);
    }
  };

  const handleVisualTargetPick = async (candidateId: string) => {
    const briefRel = activeBriefRel;
    if (!briefRel) {
      append("assistant", "还没有 Brief，无法选用北极星。");
      return;
    }
    if (!window.gameFactory?.visualTargetPick) {
      append("assistant", "当前客户端不支持选用北极星，请重启 Electron。");
      return;
    }
    const busyId = activeColleague.id;
    markBusy(busyId);
    try {
      const res = await window.gameFactory.visualTargetPick(briefRel, candidateId);
      if (res.exitCode !== 0) {
        append(
          "assistant",
          `选用失败：${(res.stderr || res.stdout || "").slice(0, 800)}`,
          undefined,
          undefined,
          ["北极星图"],
        );
        return;
      }
      const ref = res.data?.visual_reference || "";
      await refreshVisualTarget(briefRel);
      append(
        "assistant",
        `✓ 已选定北极星 \`${candidateId}\`\n\n` +
          `\`project.visual_reference\` → \`${ref}\`\n\n` +
          "视觉契约已写入 Brief。可点 **去找项目经理** 开流水线。",
        undefined,
        undefined,
        ["切换到项目经理", "切换到项目经理并生成流水线", "生成北极星图"],
      );
    } catch (e) {
      append(
        "assistant",
        `选用北极星异常：${e instanceof Error ? e.message : String(e)}`,
      );
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
          "还没有 brief。请先在 **策划** 同事那里商量并导出 Brief，再回来点「生成流水线」。",
        );
        return;
      }
      setBrief(briefRel);

      // Reuse existing manifest for this brief (Agent 可能写成了别的文件名)
      const existing =
        window.gameFactory.findManifestForBrief &&
        (await window.gameFactory.findManifestForBrief(briefRel));
      if (existing?.path) {
        setSelectedManifest(existing.path);
        await refreshManifest(existing.path);
        const meta =
          existing.meta || (await window.gameFactory.getManifestMeta(existing.path));
        append(
          "assistant",
          summarizeManifest(existing.path, meta) + "\n\n（已按 Brief 匹配到现有清单，未重复生成。）",
          undefined,
          undefined,
          ["北极星图", "运行资产生成（含文案）", "打开看板"],
        );
        setSidePanel("board");
        return;
      }

      const targets = planTargetsFromBrief(briefRel);
      append(
        "assistant",
        `正在生成流水线任务清单…\n\nBrief: \`${targets.briefRel}\`\n将写入: \`${targets.manifestRel}\``,
      );
      const res = await window.gameFactory.pipelinePlan(targets);
      if (res.exitCode !== 0) throw new Error(res.stderr || "plan failed");

      const matched =
        (window.gameFactory.findManifestForBrief &&
          (await window.gameFactory.findManifestForBrief(briefRel))) ||
        null;
      const manifestRel = matched?.path || targets.manifestRel;
      setSelectedManifest(manifestRel);
      await refreshManifest(manifestRel);
      const meta =
        matched?.meta || (await window.gameFactory.getManifestMeta(manifestRel));
      append(
        "assistant",
        summarizeManifest(manifestRel, meta) +
          `\nGodot 工程：\`${targets.godotProjectRel}\``,
        undefined,
        undefined,
        ["北极星图", "运行资产生成（含文案）", "打开看板"],
      );
      setSidePanel("board");
    } catch (e) {
      append("assistant", `生成流水线失败：${e instanceof Error ? e.message : String(e)}`);
    } finally {
      clearBusy(busyId);
    }
  };

  const handleSwitchToProductHost = useCallback(
    (opts?: { runPlan?: boolean; briefRel?: string | null }) => {
      const pm = chatStore.roster.find((c) => c.roleKind === "product_host");
      if (!pm) {
        append("assistant", "还没有项目经理同事。请用左侧「+ 雇佣」添加一位项目经理。");
        return null;
      }
      patchChatStore((prev) => setActiveInstance(prev, pm.id));
      setBrainstormChoices([]);
      setBrainstormReady(false);
      setAgentActionChoices(["生成流水线", "运行资产生成（含文案）", "打开看板"]);
      const sessionId =
        chatStore.activeByInstance[pm.id] ||
        chatStore.sessions.find((s) => s.instanceId === pm.id)?.id;
      if (sessionId) {
        append(
          "assistant",
          opts?.briefRel
            ? `已切到 **${pm.displayName}**。Brief：\`${opts.briefRel}\`\n\n点下方「生成流水线」即可（右侧会出现任务看板），再点「运行资产生成」。不必记斜杠命令。`
            : `已切到 **${pm.displayName}**。点下方按钮生成流水线 / 跑资产，或直接说要推进什么。`,
          undefined,
          { instanceId: pm.id, sessionId },
          ["生成流水线", "运行资产生成（含文案）", "打开看板"],
        );
      }
      if (opts?.runPlan) {
        window.setTimeout(() => {
          void handlePlan(opts.briefRel || undefined);
        }, 0);
      }
      return pm;
    },
    [
      chatStore.roster,
      chatStore.activeByInstance,
      chatStore.sessions,
      patchChatStore,
      append,
    ],
  );

  const handleOpenGodot = async () => {
    let projectRel = activeBriefRel ? planTargetsFromBrief(activeBriefRel).godotProjectRel : null;
    if (selectedManifest) {
      const meta = await window.gameFactory.getManifestMeta(selectedManifest);
      if (meta?.godot_project) projectRel = meta.godot_project;
    }
    if (!projectRel) {
      append("assistant", "还没有 Godot 工程路径。请先找 **项目经理** 点「生成流水线」。");
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
    const trimmed = text.trim();
    if (trimmed === "切换到程序员") {
      const tid = pendingTargetProgrammer.current || undefined;
      pendingTargetProgrammer.current = null;
      handleSwitchToProgrammer(tid);
      return;
    }
    if (trimmed === "切换到项目经理") {
      handleSwitchToProductHost({ briefRel: activeBriefRel });
      return;
    }
    if (trimmed === "切换到项目经理并生成流水线") {
      handleSwitchToProductHost({ runPlan: true, briefRel: activeBriefRel });
      return;
    }
    if (trimmed === "打开环境" || trimmed === "打开环境面板") {
      toggleSidePanel("env");
      append("assistant", "已打开右侧「环境」面板。可点「重新检测」；有红色项把原文发给支持。");
      return;
    }
    if (trimmed === "打开设置") {
      toggleSidePanel("settings");
      append("assistant", "已打开设置。填入 API Key 后请点顶部「重新检测」。");
      return;
    }
    if (trimmed === "生成流水线") {
      if (agentRole !== "product_host" && agentRole !== "brief") {
        append("assistant", "生成流水线请切换到 **项目经理**（左侧同事列表）。");
        return;
      }
      await handlePlan();
      return;
    }
    if (trimmed === "都不满意，换风格" || trimmed === "换风格" || trimmed === "重新定风格") {
      if (agentRole !== "brief") {
        append(
          "assistant",
          "换风格请切到 **策划**：改 `art_direction`（画风/调色/比例参考），再点「生成北极星图」。\n\n左侧点「策划」，直接说想要的新风格，例如：「改成更暗黑赛博、粗描边、少写实」。",
          undefined,
          undefined,
          ["生成北极星图"],
        );
        return;
      }
      append(
        "assistant",
        "好。北极星候选作废，我们先改风格再重生成。\n\n请用一两句话描述新方向（会写入 `art_direction`），例如：\n- 「更暗黑、高对比、粗描边 Q 版」\n- 「改成像素风，参考星露谷物语」\n- 「去掉厨房乱炖感，改成干净日系体育漫画」\n\n说完后我会更新草案；你再点「生成北极星图」。",
        undefined,
        undefined,
        ["生成北极星图"],
      );
      setBrainstormActive(true);
      setBrainstormChoices(["生成北极星图"]);
      return;
    }
    if (trimmed === "北极星图" || trimmed === "生成北极星" || trimmed === "生成北极星图") {
      await handleVisualTargetGenerate();
      return;
    }
    {
      const pickMatch = trimmed.match(/^选用北极星\s*([a-dA-D])$/);
      if (pickMatch) {
        await handleVisualTargetPick(pickMatch[1].toLowerCase());
        return;
      }
    }
    if (trimmed === "运行资产生成（含文案）") {
      await handleRun(true);
      return;
    }
    if (trimmed === "运行资产生成" || trimmed === "运行 Pipeline") {
      await handleRun(false);
      return;
    }
    if (trimmed === "打开看板") {
      toggleSidePanel("board");
      append("assistant", "已打开右侧任务看板。");
      return;
    }
    if (pendingSafeActions.current.has(trimmed)) {
      await handleSafeAction(trimmed);
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
        setBriefDraft(null);
        setDraftDocument(null);
        setBriefDraftStatus(null);
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
      if (cmd.action === "autofix") {
        await handleBriefAutofix(cmd.maxRounds ?? 5);
        return;
      }
      if (cmd.action === "status") {
        const res = await window.gameFactory.hostChatStatus(activeSession.id);
        const d = res.data;
        if (!d?.exists) {
          appendAssistant("当前没有进行中的 Brief 会话。发送 `/brief` 或描述游戏想法开始。");
          return;
        }
        applyDraftFromPayload(d);
        if (d.draft_brief) setBriefDraft(d.draft_brief);
        appendAssistant(
          `**Brief 会话**\n\n标题：${d.title || "（未定）"}\n资产数：${d.asset_count ?? 0}\n文档：${d.has_document ? d.document_title || "有" : "无"}\n轮次：${d.message_count ?? 0}\n模式：${d.mode || "chat"}\n可导出：${d.ready_to_export ? "是" : "否"}\n\n完整内容见顶部 **文档** 侧栏。`,
          d.last_choices,
        );
        setBrainstormActive(true);
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
            className={`btn btn--ghost ${sidePanel === "docs" ? "btn--active" : ""}`}
            onClick={() => {
              toggleSidePanel("docs");
              if (agentRole === "brief") void refreshBrainstormStatus();
            }}
          >
            文档
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
        healthOk={envHealth ? envHealth.ok : null}
        scanError={envScanError}
        onScan={() => void refreshEnv().then((r) => {
          if (r?.health) {
            append("assistant", formatEnvHealthChat(r.health), undefined, undefined, [
              "打开环境",
              ...(r.health.ok ? [] : ["打开设置"]),
            ]);
            if (!r.health.ok) setToolchainDismissed(false);
          }
        })}
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
            busyHint={busyHint}
            agentRole={agentRole}
            agentLabel={activeColleague.displayName}
            onSuggestion={handleSend}
            heroTitle={hero.title}
            heroSubtitle={hero.subtitle}
            suggestions={suggestions}
          />
          {agentRole === "brief" && activeBriefRel && (
            <div className="pm-sticky-actions" role="toolbar" aria-label="视觉定稿">
              <span className="pm-sticky-actions__label">视觉定稿</span>
              <span className="pm-sticky-actions__hint">
                {visualReferenceReady
                  ? "✓ 北极星已写入 brief · 可交给项目经理跑流水线"
                  : "Brief 已保存 · 建议先生成并选用北极星图"}
              </span>
              <button
                type="button"
                className={
                  "pm-sticky-actions__btn" +
                  (visualReferenceReady
                    ? " pm-sticky-actions__btn--done"
                    : " pm-sticky-actions__btn--primary")
                }
                disabled={chatBusy}
                onClick={() => void handleSend("生成北极星图")}
                title="生成整屏玩法预览候选并选用一张写入 visual_reference"
              >
                {visualReferenceReady ? "✓ 北极星图" : "生成北极星图"}
              </button>
              <button
                type="button"
                className={
                  "pm-sticky-actions__btn" +
                  (visualReferenceReady ? " pm-sticky-actions__btn--primary" : "")
                }
                disabled={chatBusy}
                onClick={() => void handleSend("切换到项目经理")}
                title="把已定稿 brief 交给项目经理开流水线"
              >
                去找项目经理
              </button>
            </div>
          )}
          {agentRole === "product_host" && (
            <div className="pm-sticky-actions" role="toolbar" aria-label="项目推进">
              <span className="pm-sticky-actions__label">推进项目</span>
              <span className="pm-sticky-actions__hint">
                {!selectedManifest
                  ? "先点蓝钮生成任务清单"
                  : !visualReferenceReady
                    ? "建议回策划选定北极星后再跑资产（也可直接跑）"
                    : `✓ 清单就绪${tasks.length ? ` · ${tasks.length} 任务` : ""} · 蓝钮 = 跑资产`}
              </span>
              <button
                type="button"
                className={
                  "pm-sticky-actions__btn" +
                  (selectedManifest ? " pm-sticky-actions__btn--done" : " pm-sticky-actions__btn--primary")
                }
                disabled={chatBusy}
                onClick={() => void handleSend("生成流水线")}
                title="从 Brief 生成 pipeline manifest（任务清单）"
              >
                {selectedManifest ? "✓ ① 生成流水线" : "① 生成流水线"}
              </button>
              <button
                type="button"
                className={
                  "pm-sticky-actions__btn" +
                  (selectedManifest ? " pm-sticky-actions__btn--primary" : "")
                }
                disabled={chatBusy}
                onClick={() => void handleSend("运行资产生成（含文案）")}
                title="执行管线：出图/出视频（已完成任务会跳过）"
              >
                ② 运行资产生成
              </button>
              <button
                type="button"
                className="pm-sticky-actions__btn"
                disabled={chatBusy}
                onClick={() => void handleSend("打开看板")}
                title="右侧查看任务 DAG"
              >
                看板
              </button>
            </div>
          )}
          <ChatInput
            disabled={chatBusy}
            choices={
              agentRole === "brief"
                ? brainstormChoices.filter(
                    (c) =>
                      !["生成北极星图", "生成北极星", "北极星图", "都不满意，换风格"].includes(c),
                  )
                : agentRole === "product_host"
                  ? agentActionChoices.filter(
                      (c) =>
                        ![
                          "生成流水线",
                          "北极星图",
                          "生成北极星",
                          "生成北极星图",
                          "运行资产生成",
                          "运行资产生成（含文案）",
                          "打开看板",
                        ].includes(c),
                    )
                  : agentActionChoices
            }
            readyToExport={agentRole === "brief" && brainstormReady}
            showAutofix={
              agentRole === "brief" && Boolean(briefDraftStatus?.gaps && briefDraftStatus.gaps.length > 0)
            }
            placeholder={
              agentRole === "brief"
                ? "描述游戏想法，和策划商量设定…"
                : agentRole === "product_host"
                  ? "描述试玩问题或要推进的事…"
                  : "描述要改的代码或任务…"
            }
            hint={
              agentRole === "brief"
                ? "Enter 发送 · 气泡内选项可点 · 保存 Brief 后可生成北极星"
                : agentRole === "product_host"
                  ? "上方：① 流水线 → ② 跑资产（蓝 = 建议下一步）"
                  : "Enter 发送 · 经执行器 CLI 回信 · 「文档」可预览项目文件"
            }
            onSend={handleSend}
            onChoice={(text) => {
              if (text === "保存 Brief") {
                void handleBriefExport();
                return;
              }
              void handleSend(text);
            }}
            onAutofix={agentRole === "brief" ? () => void handleBriefAutofix(5) : undefined}
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

        {sidePanel === "docs" && (
          <DocsPreviewPanel
            draftBrief={briefDraft}
            draftDocument={draftDocument}
            status={briefDraftStatus}
            activeBriefRel={activeBriefRel}
            readyToExport={brainstormReady}
            busy={chatBusy}
            onRefresh={() => {
              if (agentRole === "brief") void refreshBrainstormStatus();
            }}
            onAutofix={agentRole === "brief" ? () => void handleBriefAutofix(5) : undefined}
            onExportBrief={agentRole === "brief" ? () => void handleBriefExport() : undefined}
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

      {((toolchainReport?.needs_attention && !toolchainDismissed) ||
        (envHealth && !envHealth.ok && !toolchainDismissed)) &&
        (toolchainReport || envHealth) && (
        <ToolchainModal
          report={
            toolchainReport || {
              toolchain_root: "",
              bin_dir: "",
              components: [],
              missing_required: [],
              missing_optional: [],
              needs_attention: true,
            }
          }
          extraIssues={envHealth?.blocking || []}
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
