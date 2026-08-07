import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ManifestMeta, PipelineStatus, PipelineTask } from "./vite-env.d";
import {
  makeabilityCardAfterServerPatch,
  makeabilityCardLocalSubmitPatch,
} from "./chat/makeabilityCardStatus";
import { ChatView } from "./components/ChatView";
import { ChatInput } from "./components/ChatInput";
import { ColleagueConfigBar } from "./components/ColleagueConfigBar";
import { ColleagueRoster } from "./components/ColleagueRoster";
import { HireColleagueModal } from "./components/HireColleagueModal";
import { NewProjectModal } from "./components/NewProjectModal";
import { BoardPanel } from "./components/BoardPanel";
import {
  briefMakeabilityExportReady,
  briefMakeabilityGateHint,
} from "./components/briefPreviewFormat";
import { AssetReviewPanel } from "./components/AssetReviewPanel";
import { DocsPreviewPanel } from "./components/DocsPreviewPanel";
import { ProjectSwitcher } from "./components/ProjectSwitcher";
import { SettingsPage, type SettingsPageTab } from "./components/SettingsPage";
import { ToolchainModal } from "./components/ToolchainModal";
import { UpdateBanner } from "./components/UpdateBanner";
import { EnvToolbar } from "./components/EnvToolbar";
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
  clearActiveBriefRel,
  isExternalBriefRel,
  isIsolatedBriefRel,
  loadActiveBriefRel,
  loadActiveBriefRelForStartup,
  loadLastBriefRel,
  parseDeltaCommand,
  parseExternalBriefId,
  parsePlanSubcommand,
  planTargetsFromBrief,
  planTargetsFromExternalEntry,
  projectRootFromBriefRel,
  readActiveBriefPreference,
  sameProjectRoot,
  sanitizeProjectSlug,
  saveActiveBriefRel,
  slugFromBriefRel,
  type ExternalProjectEntry,
  type PlanTargets,
} from "./chat/projectPaths";
import { parseNewProjectIntent } from "./chat/newProjectIntent";
import { resolveAppendTarget, sessionTargetForInstance } from "./chat/appendTarget";
import { isAgentChatRole, routeColleagueSend } from "./chat/colleagueSendRoute";
import {
  formatVtGlobalChoiceLabel,
  formatVtProgressBoard,
  formatVtSceneChoiceLabel,
  formatVtStickyHint,
  type VtGlobalMark,
  type VtSceneMark,
} from "./chat/vtProgressFormat";
import {
  formatVtRestyleChoice,
  formatVtRegenAfterFeedbackChoice,
  parseVtRestyleChoice,
  parseVtRegenAfterFeedbackChoice,
  wrapVtRestyleUserMessage,
  isVtRestyleClarificationAsk,
  type VtRestyleFocus,
} from "./chat/vtRestyleRoute";
import { formatVtPickChoice, parseVtPickChoice, extractSceneIdFromChoice } from "./chat/vtChoiceParse";
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
import {
  loadAgentInstancesFromConfig,
  serializeAgentInstances,
  upsertInstanceRecord,
  shouldSyncCodexThirdParty,
} from "./settings/agentInstances";
import { executorKindForHire, type HireColleagueConfirmPayload } from "./settings/hireColleague";
type SidePanel = "board" | "assets" | "docs" | null;
type AppView = "chat" | "settings";

function slugifyBriefName(raw: string): string {
  const t = raw.trim().toLowerCase();
  if (/[\u4e00-\u9fff]/.test(t)) {
    return `game-${Date.now().toString(36)}`;
  }
  const slug = t.replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  return slug || `game-${Date.now().toString(36)}`;
}

type DiagnoseItem = {
  task_id?: string;
  kind?: string;
  summary?: string;
  pm_fit?: string;
  pm_tip?: string;
};

/** Format diagnose JSON into a clear「适不适合项目经理」tip for chat. */
function formatPmFitAdvice(data: {
  pm_fit?: string;
  pm_suitable?: boolean;
  pm_advice?: string;
  pm_advice_short?: string;
  items?: DiagnoseItem[];
  needs_hermes?: DiagnoseItem[];
} | null | undefined): { suitable: boolean; headline: string; detail: string } {
  if (!data) {
    return {
      suitable: false,
      headline: "未能诊断失败原因",
      detail: "可打开看板查看 failed 任务，或重试「项目经理处理失败」。",
    };
  }
  const items = (data.items?.length ? data.items : data.needs_hermes) || [];
  const lines = items.slice(0, 6).map((n) => {
    const fit =
      n.pm_fit === "yes" ? "适合" : n.pm_fit === "no" ? "不必" : n.pm_fit === "maybe" ? "可分诊" : "?";
    const tip = n.pm_tip || n.summary || "";
    return `- \`${n.task_id || "?"}\`（${n.kind || "?"}）· **${fit}**${tip ? ` — ${tip}` : ""}`;
  });
  const headline =
    data.pm_advice_short ||
    (data.pm_suitable ? "适合项目经理直接处理" : "不必找项目经理");
  const detail =
    (data.pm_advice ? `${data.pm_advice}\n\n` : "") +
    (lines.length ? `逐项：\n${lines.join("\n")}` : "");
  return { suitable: Boolean(data.pm_suitable), headline, detail };
}

type PipelineRunPayload = {
  complete?: boolean;
  paused?: boolean;
  blocked?: boolean;
  message?: string;
  last_task?: string;
  last_exit_code?: number;
  summary?: {
    counts?: Record<string, number>;
    failed_ids?: string[];
    ready_ids?: string[];
    ready_count?: number;
    done?: boolean;
  };
};

/** User cancelled an in-flight chat/CLI turn (Stop button). */
function isChatAborted(res: {
  aborted?: boolean;
  exitCode?: number;
  data?: unknown;
} | null | undefined): boolean {
  if (!res) return false;
  if (res.aborted) return true;
  if (res.exitCode === 130) return true;
  const data = res.data as { aborted?: boolean; error?: string } | null | undefined;
  if (data?.aborted) return true;
  return String(data?.error || "").trim() === "已停止";
}

function isAbortError(e: unknown): boolean {
  const msg = e instanceof Error ? e.message : String(e || "");
  return /已停止|aborted|cancelled|canceled/i.test(msg);
}

/** Clear stop notice + recommended next action for pipeline pause / incomplete run. */
function planPipelineStop(opts: {
  exitCode: number;
  runData?: PipelineRunPayload | null;
  advice: ReturnType<typeof formatPmFitAdvice>;
  healed: string[];
  status?: PipelineStatus | null;
}): { title: string; body: string; choices: string[] } {
  const summary = opts.status || opts.runData?.summary;
  const counts = summary?.counts || {};
  const done = Number(counts.done ?? 0);
  const pending = Number(counts.pending ?? 0);
  const failedN = Number(
    counts.failed ?? opts.status?.failed_ids?.length ?? opts.runData?.summary?.failed_ids?.length ?? 0,
  );
  const ready =
    opts.status?.ready_ids?.length ??
    opts.runData?.summary?.ready_ids?.length ??
    opts.runData?.summary?.ready_count ??
    0;
  const progress = `进度：完成 ${done} · 待跑 ${pending}` + (failedN ? ` · 失败 ${failedN}` : "");
  const last = opts.runData?.last_task
    ? `\n停在：\`${opts.runData.last_task}\`` +
      (opts.runData.last_exit_code != null ? `（exit ${opts.runData.last_exit_code}）` : "")
    : "";
  const paused = Boolean(opts.runData?.paused) || opts.exitCode === 2 || failedN > 0;
  const blocked = Boolean(opts.runData?.blocked);

  if (paused && failedN > 0) {
    if (opts.advice.suitable) {
      return {
        title: "流水线已暂停",
        body:
          `默认遇失败即停，已完成的任务会保留。\n${progress}${last}\n\n` +
          `**推荐下一步 → 项目经理处理失败**\n` +
          `（${opts.advice.headline}）\n\n${opts.advice.detail}` +
          (opts.healed.length
            ? `\n\n另已自动复位 ${opts.healed.length} 项（网络/缺文件），处理后可一并续跑。`
            : ""),
        choices: ["项目经理处理失败", "运行资产生成", "打开看板"],
      };
    }
    if (opts.healed.length) {
      return {
        title: "流水线已暂停（可修项已复位）",
        body:
          `${progress}${last}\n\n` +
          `已自动复位：${opts.healed.slice(0, 6).join(", ")}${opts.healed.length > 6 ? "…" : ""}\n` +
          `（${opts.advice.headline}）\n\n` +
          `**推荐下一步 → 运行资产生成**（续跑）`,
        choices: ["运行资产生成", "打开看板"],
      };
    }
    return {
      title: "流水线已暂停",
      body:
        `默认遇失败即停，已完成的任务会保留。\n${progress}${last}\n\n` +
        `**推荐下一步 → 运行资产生成**\n` +
        `（${opts.advice.headline}）\n\n${opts.advice.detail}`,
      choices: ["运行资产生成", "运行资产生成（含文案）", "打开看板"],
    };
  }

  if (blocked) {
    return {
      title: "流水线卡住了",
      body:
        `${progress}\n` +
        (opts.runData?.message ? `${opts.runData.message}\n` : "") +
        `\n常见原因：上游失败未清、缺文案 plan、或缺依赖产物。\n\n` +
        `**推荐下一步 → 打开看板** 看哪条红了；若有失败再点「项目经理处理失败」。`,
      choices: ["打开看板", "项目经理处理失败", "运行资产生成（含文案）"],
    };
  }

  if (ready > 0 || pending > 0) {
    return {
      title: "本轮已停下，还有任务未跑完",
      body:
        `${progress}` +
        (ready > 0 ? `（其中 ${ready} 个已就绪）` : "") +
        `${last}\n\n` +
        `**推荐下一步 → 运行资产生成**（续跑，已完成的会跳过）`,
      choices: ["运行资产生成", "运行资产生成（含文案）", "打开看板"],
    };
  }

  return {
    title: "流水线已结束",
    body: `${progress}${last}\n\n可打开看板确认，或继续派工给程序员。`,
    choices: ["打开看板"],
  };
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
  const [assetsManifestRel, setAssetsManifestRel] = useState<string | null>(null);
  const [activeBriefRel, setActiveBriefRel] = useState<string | null>(() =>
    loadActiveBriefRelForStartup(),
  );
  const [externalEntryById, setExternalEntryById] = useState<Record<string, ExternalProjectEntry>>({});
  /** brief.project.visual_reference is a real image path on disk */
  const [visualReferenceReady, setVisualReferenceReady] = useState(false);
  /** Global VT pick mark (brief bind and/or selected.png) */
  const [vtGlobalMark, setVtGlobalMark] = useState<VtGlobalMark>({});
  /** scenes from visual-target status (fallback when draft has no scenes) */
  const [vtScenesFromStatus, setVtScenesFromStatus] = useState<VtSceneMark[]>([]);
  const [tasks, setTasks] = useState<PipelineTask[]>([]);
  const [status, setStatus] = useState<PipelineStatus | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [chatStore, setChatStore] = useState<ChatSessionStore>(() => loadSessionStore());
  const chatStoreRef = useRef(chatStore);
  chatStoreRef.current = chatStore;
  const [sidePanel, setSidePanel] = useState<SidePanel>(null);
  const [sidePanelWidth, setSidePanelWidth] = useState<number | null>(() => {
    const v = localStorage.getItem("sidePanelWidth");
    return v ? Number(v) : null;
  });
  const isResizingPanel = useRef(false);
  const resizeStartX = useRef(0);
  const resizeStartW = useRef(0);
  const [appView, setAppView] = useState<AppView>("chat");
  const [settingsTab, setSettingsTab] = useState<SettingsPageTab>("providers");
  /** 正在等待回复的同事 instanceId（可并行；避免一人转圈三人一起 loading） */
  const [busyInstanceIds, setBusyInstanceIds] = useState<string[]>([]);
  /** markBusy 时钉住发起会话，避免切同事后无 target 的 append 写到当前窗 */
  const appendOriginByBusyRef = useRef<Map<string, { instanceId: string; sessionId: string }>>(
    new Map(),
  );
  const markBusy = useCallback((instanceId: string) => {
    const store = loadSessionStore();
    const pinned = sessionTargetForInstance(store, instanceId);
    if (pinned) {
      appendOriginByBusyRef.current.set(instanceId, pinned);
    }
    setBusyInstanceIds((prev) => (prev.includes(instanceId) ? prev : [...prev, instanceId]));
  }, []);
  const clearBusy = useCallback((instanceId: string) => {
    appendOriginByBusyRef.current.delete(instanceId);
    setBusyInstanceIds((prev) => prev.filter((id) => id !== instanceId));
  }, []);
  const anyBusy = busyInstanceIds.length > 0;
  const [brainstormActive, setBrainstormActive] = useState(false);
  const [brainstormChoices, setBrainstormChoices] = useState<string[]>([]);
  const [brainstormReady, setBrainstormReady] = useState(false);
  const [docsDiskRefreshKey, setDocsDiskRefreshKey] = useState(0);
  const [docsFocusDiskRel, setDocsFocusDiskRel] = useState<string | null>(null);
  const [newProjectOpen, setNewProjectOpen] = useState(false);
  const [newProjectDefaultSlug, setNewProjectDefaultSlug] = useState("fishing-2d");
  const pendingNewProjectRef = useRef<{
    seed?: string;
    userText?: string;
    announcePath?: boolean;
  } | null>(null);
  const [draftTitle, setDraftTitle] = useState("");
  const [briefDraft, setBriefDraft] = useState<HostChatDraftBrief | null>(null);
  const [draftDocument, setDraftDocument] = useState<HostChatDraftDocument | null>(null);
  const [briefDraftStatus, setBriefDraftStatus] = useState<HostChatStatus | null>(null);
  const [toolchainReport, setToolchainReport] = useState<ToolchainReport | null>(null);
  const [toolchainDismissed, setToolchainDismissed] = useState(false);
  const [toolchainInstalling, setToolchainInstalling] = useState<string | null>(null);
  const [toolchainLog, setToolchainLog] = useState<string[]>([]);
  const [hireRoleKind, setHireRoleKind] = useState<ChatAgentRole | null>(null);
  const autoEnsureDone = useRef(false);
  /** IT「信任本会话」内存覆盖，避免关信任后立刻发消息仍读到旧磁盘值 */
  const itSessionTrustRef = useRef<Record<string, boolean>>({});
  /** Soft-gate: warn once before pipeline run without visual_reference */
  const runWithoutVtWarned = useRef(false);
  /** Scene id used for the latest visual-target generate (null = global) */
  const pendingVtSceneIdRef = useRef<string | null>(null);
  /** After「都不满意」keep regenerating / brainstorming on this scope */
  const vtRestyleFocusRef = useRef<VtRestyleFocus>({ active: false, sceneId: null });
  /** UI mirror of restyle lock (ref alone does not re-render input placeholder) */
  const [vtRestyleAwaitingText, setVtRestyleAwaitingText] = useState(false);
  /** Latest generate target — pick only reuses manifest when scene scope matches */
  const pendingVtGenerateRef = useRef<{
    manifestPath: string;
    sceneId: string | null;
  } | null>(null);
  /** Last pick source for 「也用于」assign (scene id or null = global) */
  const lastVtPickSourceRef = useRef<{ kind: "global" | "scene"; sceneId?: string } | null>(
    null,
  );
  /** Stable handle so early callbacks can sync board after brief changes */
  const syncPipelineForBriefRef = useRef<(briefRel: string | null) => Promise<string | null>>(
    async () => null,
  );
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

  const [agentConfigSaving, setAgentConfigSaving] = useState(false);
  const agentConfigSavingRef = useRef(false);
  /** Pending ACP/Codex/Pi approvals — drives busy-hint text when a card is waiting. */
  const [pendingToolPermissions, setPendingToolPermissions] = useState<
    Array<{
      permissionId: string;
      sessionId: string;
      instanceId?: string;
      turnId?: string;
      argvSummary: string;
      source?: "pi" | "cursor_acp" | "hermes_acp" | "codex_app_server";
    }>
  >([]);
  const pendingToolPermissionsRef = useRef(pendingToolPermissions);
  pendingToolPermissionsRef.current = pendingToolPermissions;
  const activeColleague = getActiveColleague(chatStore);
  const agentRole = activeColleague.roleKind;
  const briefExportReady = agentRole === "brief" && briefMakeabilityExportReady(briefDraftStatus);
  const briefExportGateHint = briefMakeabilityGateHint(briefDraftStatus);
  const activeSession = getActiveSession(chatStore);
  const messages = activeSession.messages;
  const chatBusy = busyInstanceIds.includes(activeColleague.id);
  const handleStopChat = useCallback(async () => {
    const id = activeColleague.id;
    if (!id) return;
    try {
      await window.gameFactory?.chatStop?.(id);
    } catch {
      /* best-effort; turn handler will settle busy */
    }
  }, [activeColleague.id]);
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
  // Persist side panel width whenever it changes
  useEffect(() => {
    if (sidePanelWidth !== null) {
      localStorage.setItem("sidePanelWidth", String(sidePanelWidth));
    }
  }, [sidePanelWidth]);

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
      setVtGlobalMark({});
      setVtScenesFromStatus([]);
      return false;
    }
    try {
      const st = await window.gameFactory.visualTargetStatus(rel);
      setVisualReferenceReady(Boolean(st.ready));
      const gSel = st.global_selected_id;
      setVtGlobalMark({
        ready: Boolean(st.global_ready),
        selected_id: gSel ? String(gSel).trim().toLowerCase() : null,
        has_selected_image: Boolean(st.global_has_selected_image),
        preview_path: st.global_preview_path
          ? String(st.global_preview_path).trim()
          : st.visual_reference
            ? String(st.visual_reference).trim()
            : null,
      });
      const scenes = Array.isArray(st.scenes)
        ? st.scenes
            .map((s) => ({
              id: String(s.id || "").trim(),
              title: String(s.title || s.id || "").trim(),
              ready: Boolean(s.ready),
              selected_id: s.selected_id
                ? String(s.selected_id).trim().toLowerCase()
                : null,
              has_selected_image: Boolean(s.has_selected_image),
              visual_reference: String(s.visual_reference || "").trim(),
              preview_path: String(s.preview_path || s.visual_reference || "").trim() || null,
            }))
            .filter((s) => Boolean(s.id))
        : [];
      setVtScenesFromStatus(scenes);
      return Boolean(st.ready);
    } catch {
      setVisualReferenceReady(false);
      setVtGlobalMark({});
      setVtScenesFromStatus([]);
      return false;
    }
  }, [activeBriefRel]);

  // Refresh north-star thumbs when opening the board
  useEffect(() => {
    if (sidePanel === "board" && activeBriefRel) {
      void refreshVisualTarget(activeBriefRel);
    }
  }, [sidePanel, activeBriefRel, refreshVisualTarget]);

  const refreshExternalProjects = useCallback(async (): Promise<Record<string, ExternalProjectEntry>> => {
    if (!window.gameFactory?.externalProjectsList) return {};
    try {
      const res = await window.gameFactory.externalProjectsList();
      const map: Record<string, ExternalProjectEntry> = {};
      for (const p of res.projects || []) {
        const id = String(p.id || "").trim();
        if (id) map[id] = p;
      }
      setExternalEntryById(map);
      return map;
    } catch {
      return {};
    }
  }, []);

  const resolvePlanTargets = useCallback(
    async (
      briefRel: string,
      cache?: Record<string, ExternalProjectEntry>,
    ): Promise<PlanTargets> => {
      const normalized = briefRel.replace(/\\/g, "/");
      if (isExternalBriefRel(normalized)) {
        const id = parseExternalBriefId(normalized);
        if (id) {
          let entry = (cache ?? externalEntryById)[id];
          if (!entry) {
            const map = await refreshExternalProjects();
            entry = map[id];
          }
          if (entry) return planTargetsFromExternalEntry(entry);
        }
      }
      return planTargetsFromBrief(normalized);
    },
    [externalEntryById, refreshExternalProjects],
  );

  const activeProjectLabel = useMemo(() => {
    if (!activeBriefRel) return null;
    if (isExternalBriefRel(activeBriefRel)) {
      const id = parseExternalBriefId(activeBriefRel);
      const entry = id ? externalEntryById[id] : null;
      return entry?.display_name || slugFromBriefRel(activeBriefRel);
    }
    return slugFromBriefRel(activeBriefRel);
  }, [activeBriefRel, externalEntryById]);

  const setBrief = useCallback((briefRel: string) => {
    const normalized = briefRel.replace(/\\/g, "/");
    setActiveBriefRel(normalized);
    saveActiveBriefRel(normalized);
    void refreshVisualTarget(normalized);
    // Canonicalize legacy resources/ ↔ cli/resources/ paths in the background.
    // Never let resolve remap projects/A → projects/B (e.g. fishing-2d before brief.json exists).
    void (async () => {
      if (isExternalBriefRel(normalized)) return;
      if (!window.gameFactory?.resolveBriefRel) return;
      const r = await window.gameFactory.resolveBriefRel(normalized);
      if (!r.path || r.path === normalized) return;
      const fromRoot = projectRootFromBriefRel(normalized);
      const toRoot = projectRootFromBriefRel(r.path);
      if (fromRoot && toRoot && fromRoot !== toRoot) return;
      if (fromRoot && !toRoot) return;
      if (r.exists || (fromRoot && toRoot === fromRoot)) {
        setActiveBriefRel(r.path);
        saveActiveBriefRel(r.path);
        void refreshVisualTarget(r.path);
      }
    })();
  }, [refreshVisualTarget]);

  /** Unbind topbar project so a new planner draft cannot silently write to the old path. */
  const clearBriefBinding = useCallback(() => {
    setActiveBriefRel(null);
    clearActiveBriefRel();
    setSelectedManifest("");
    setTasks([]);
    setStatus(null);
    setAssetsManifestRel(null);
    setVisualReferenceReady(false);
    setLogs([]);
    setDocsFocusDiskRel(null);
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

  const openSettings = useCallback((tab: SettingsPageTab = "providers") => {
    setSidePanel(null);
    setSettingsTab(tab);
    setAppView("settings");
  }, []);

  const closeSettings = useCallback(() => {
    setAppView("chat");
  }, []);

  const appendAssistant = useCallback(
    (
      content: string,
      choices?: string[],
      attachments?: ChatAttachment[],
      target?: { instanceId: string; sessionId: string },
      makeabilityCard?: import("./chat/types").MakeabilityCardState,
    ) => {
      const mergedChoices = makeabilityCard
        ? undefined
        : mergeMessageChoices(choices, content);
      const storeSnap = loadSessionStore();
      const resolved =
        resolveAppendTarget(target, storeSnap, appendOriginByBusyRef.current) || undefined;
      patchChatStore((prev) => {
        const msg = {
          id: newMessageId(),
          role: "assistant" as const,
          content,
          timestamp: Date.now(),
          choices: mergedChoices,
          attachments: attachments?.length ? attachments : undefined,
          makeabilityCard,
        };
        if (resolved) {
          return updateSessionMessages(prev, resolved.instanceId, resolved.sessionId, (msgs) => [
            ...msgs,
            msg,
          ]);
        }
        return updateActiveMessages(prev, (msgs) => [...msgs, msg]);
      });
      if (!resolved || resolved.instanceId === getActiveColleague(loadSessionStore()).id) {
        setBrainstormChoices(makeabilityCard ? [] : mergedChoices || []);
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
        llm_backend?: string | null;
        llm_pi_error?: string | null;
        has_review?: boolean;
        intent_count?: number;
        detail_count?: number;
        makeability_fingerprint_match?: boolean;
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
          llm_backend: data.llm_backend ?? (replace ? null : prev?.llm_backend),
          llm_pi_error: data.llm_pi_error ?? (replace ? null : prev?.llm_pi_error),
          has_review: data.has_review ?? (replace ? false : prev?.has_review),
          intent_count: data.intent_count ?? (replace ? 0 : prev?.intent_count),
          detail_count: data.detail_count ?? (replace ? 0 : prev?.detail_count),
          makeability_fingerprint_match:
            data.makeability_fingerprint_match ??
            (replace ? false : prev?.makeability_fingerprint_match),
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
        llm_backend?: string | null;
        llm_pi_error?: string | null;
        bound_brief_rel?: string | null;
      },
      target?: { instanceId: string; sessionId: string },
    ) => {
      if (!data.assistant_message) return;
      setBrainstormActive(true);
      let content = data.assistant_message;
      const backend = (data.llm_backend || "").trim();
      if (backend === "host" && data.llm_pi_error) {
        const err = String(data.llm_pi_error).replace(/\s+/g, " ").slice(0, 160);
        content += `\n\n—— via Host（内置 Pi 不可用：${err}）`;
      } else if (backend === "pi") {
        content += "\n\n—— via 内置 Pi";
      } else if (backend === "host") {
        content += "\n\n—— via Host";
      }
      appendAssistant(content, data.choices, undefined, target);
      applyDraftFromPayload(data);
      const bound = String(data.bound_brief_rel || "").replace(/\\/g, "/");
      if (bound && (!activeBriefRel || !sameProjectRoot(bound, activeBriefRel))) {
        setBrief(bound);
      }
    },
    [appendAssistant, applyDraftFromPayload, activeBriefRel, setBrief],
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
      const bound = String(data.bound_brief_rel || "").replace(/\\/g, "/");
      // Restore topbar if session still bound but UI lost the selection (docs / 视觉定稿)
      if (bound && (!activeBriefRel || !sameProjectRoot(bound, activeBriefRel))) {
        setBrief(bound);
      }
    } else {
      setBriefDraft(null);
      setDraftDocument(null);
      setBriefDraftStatus(null);
    }
  }, [applyDraftFromPayload, activeBriefRel, setBrief]);

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
      const storeSnap = loadSessionStore();
      const resolved =
        resolveAppendTarget(target, storeSnap, appendOriginByBusyRef.current) || undefined;
      patchChatStore((prev) => {
        const msg = {
          id: newMessageId(),
          role,
          content,
          timestamp: Date.now(),
          attachments: attachments?.length ? attachments : undefined,
          choices: merged,
        };
        if (resolved) {
          return updateSessionMessages(prev, resolved.instanceId, resolved.sessionId, (msgs) => [
            ...msgs,
            msg,
          ]);
        }
        return updateActiveMessages(prev, (msgs) => [...msgs, msg]);
      });
      if (
        merged?.length &&
        (!resolved || resolved.instanceId === getActiveColleague(loadSessionStore()).id)
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

  const handleToolPermissionDecision = useCallback(
    async (permissionId: string, decision: "once" | "turn" | "session" | "deny") => {
      const statusMap = {
        once: "allowed_once",
        turn: "allowed_turn",
        session: "allowed_session",
        deny: "denied",
      } as const;
      setPendingToolPermissions((prev) => prev.filter((p) => p.permissionId !== permissionId));
      patchChatStore((store) => ({
        ...store,
        sessions: store.sessions.map((s) => ({
          ...s,
          messages: s.messages.map((m) =>
            m.toolPermission?.permissionId === permissionId &&
            m.toolPermission.status === "pending"
              ? {
                  ...m,
                  toolPermission: {
                    ...m.toolPermission,
                    status: statusMap[decision],
                  },
                }
              : m,
          ),
        })),
      }));
      try {
        await window.gameFactory?.decideToolPermission?.(permissionId, decision);
      } catch {
        /* bridge may have timed out */
      }
    },
    [patchChatStore],
  );

  const handleSelectColleague = useCallback(
    (instanceId: string) => {
      patchChatStore((prev) => setActiveInstance(prev, instanceId));
      pendingSafeActions.current = new Map();
      setBrainstormActive(false);
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

  const handleRequestHire = useCallback((roleKind: ChatAgentRole) => {
    setHireRoleKind(roleKind);
  }, []);

  const handleHireConfirm = useCallback(
    (payload: HireColleagueConfirmPayload) => {
      let hiredId = "";
      const exec = executorKindForHire(payload.record);
      patchChatStore((prev) => {
        const next = hireColleague(prev, payload.roleKind, payload.displayName, exec);
        hiredId = next.activeInstanceId;
        return next;
      });
      setHireRoleKind(null);
      setBrainstormActive(false);
      setBrainstormReady(false);
      setBrainstormChoices([]);
      setDraftTitle("");
      void (async () => {
        if (!hiredId || !window.gameFactory?.saveConfig) return;
        try {
          const info = await window.gameFactory.getConfig();
          const instances = loadAgentInstancesFromConfig(info.data as Record<string, unknown>);
          const nextMap = upsertInstanceRecord(instances, hiredId, payload.record);
          await window.gameFactory.saveConfig({
            agents: {
              instances: serializeAgentInstances(nextMap),
            },
          });
          if (
            shouldSyncCodexThirdParty(payload.record) &&
            window.gameFactory.executorStep
          ) {
            await window.gameFactory.executorStep("codex", "sync_api", {
              instanceId: hiredId,
            });
          }
        } catch {
          /* config persist best-effort */
        }
      })();
    },
    [patchChatStore],
  );

  const handleHireCancel = useCallback(() => {
    setHireRoleKind(null);
  }, []);

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
      void window.gameFactory?.stopAgentAcpInstance?.(instanceId)?.catch?.(() => {});
      void (async () => {
        if (!window.gameFactory?.saveConfig) return;
        try {
          await window.gameFactory.saveConfig({
            agents: {
              instances: { [instanceId]: null },
            },
          });
        } catch {
          /* config cleanup best-effort */
        }
      })();
    },
    [patchChatStore],
  );

  const handleNewChat = useCallback(() => {
    // Keep the same project on 「新对话」— only 「新建项目」should unbind.
    // Clearing used to leave list history but drop activeBriefRel, so docs / 视觉定稿 bar vanished.
    const keepBrief = agentRole === "brief" ? activeBriefRel : null;
    let newSessionId: string | null = null;
    patchChatStore((prev) => {
      const next = startNewSession(prev, prev.activeInstanceId);
      newSessionId = next.activeByInstance[prev.activeInstanceId] || null;
      return next;
    });
    setBrainstormActive(false);
    setBrainstormReady(false);
    setBrainstormChoices([]);
    setDraftTitle("");
    setBriefDraft(null);
    setDraftDocument(null);
    setBriefDraftStatus(null);
    if (keepBrief && newSessionId && window.gameFactory?.hostChatBind) {
      void window.gameFactory.hostChatBind(newSessionId, keepBrief).then((res) => {
        const data = res?.data;
        if (!data) return;
        applyDraftFromPayload(
          {
            draft_brief: data.draft_brief ?? null,
            title: data.title,
            asset_count: data.asset_count,
          },
          { replace: true },
        );
        if (data.draft_brief) setBriefDraft(data.draft_brief);
      });
    }
  }, [patchChatStore, agentRole, activeBriefRel, applyDraftFromPayload]);

  /** Create projects/<slug>/ and bind topbar before brief.json exists. */
  const ensureAndBindProject = useCallback(
    async (slugHint?: string): Promise<{ slug: string; briefRel: string; guideRel?: string } | null> => {
      if (!window.gameFactory?.ensureProject) {
        appendAssistant("当前 GUI 不支持创建工程目录，请重启 Foundry。");
        return null;
      }
      const slug = sanitizeProjectSlug(slugHint || "");
      if (!slug) {
        // Electron often blocks window.prompt — caller must open NewProjectModal.
        return null;
      }
      const res = await window.gameFactory.ensureProject(slug);
      if (!res.ok || !res.briefRel) {
        appendAssistant(`创建工程失败：${res.error || "unknown"}`);
        return null;
      }
      setBrief(res.briefRel);
      setSelectedManifest("");
      setTasks([]);
      setStatus(null);
      setDocsFocusDiskRel(res.guideRel || `${res.projectRootRel}/工程说明.md`);
      setDocsDiskRefreshKey((n) => n + 1);
      return {
        slug: res.slug || slug,
        briefRel: res.briefRel,
        guideRel: res.guideRel,
      };
    },
    [appendAssistant, setBrief],
  );

  const openNewProjectModal = useCallback(
    (opts?: { seed?: string; userText?: string; announcePath?: boolean; defaultSlug?: string }) => {
      pendingNewProjectRef.current = {
        seed: opts?.seed,
        userText: opts?.userText,
        announcePath: opts?.announcePath,
      };
      setNewProjectDefaultSlug(opts?.defaultSlug || "fishing-2d");
      setNewProjectOpen(true);
    },
    [],
  );

  /** Discard host-chat draft, then create+bind a project folder. */
  const runBriefReset = useCallback(
    async (seed?: string, opts?: { announcePath?: boolean; userText?: string; slugHint?: string }) => {
      const slugFromSeed = sanitizeProjectSlug(opts?.slugHint || "");
      if (!slugFromSeed) {
        openNewProjectModal({
          seed,
          userText: opts?.userText,
          announcePath: opts?.announcePath,
          defaultSlug: "fishing-2d",
        });
        return;
      }

      const busyId = activeColleague.id;
      const nextStore = startNewSession(chatStore, busyId);
      const newSessionId = nextStore.activeByInstance[busyId] || getActiveSession(nextStore).id;
      const sessionTarget = { instanceId: busyId, sessionId: newSessionId };
      patchChatStore(() => nextStore);
      clearBriefBinding();
      setBrainstormActive(false);
      setBrainstormReady(false);
      setBriefDraft(null);
      setDraftDocument(null);
      setBriefDraftStatus(null);
      setDraftTitle("");

      const created = await ensureAndBindProject(slugFromSeed);
      if (!created) {
        appendAssistant(
          "创建工程失败。请再点顶栏「新建项目」，或发送「新建项目 fishing-2d」。",
          undefined,
          undefined,
          sessionTarget,
        );
        return;
      }

      if (opts?.userText?.trim()) {
        append("user", opts.userText, undefined, sessionTarget);
      }
      markBusy(busyId);
      setBrainstormChoices([]);
      const seedTrim = (seed || "").trim();
      const seedIsSlugOnly = Boolean(seedTrim && sanitizeProjectSlug(seedTrim) === seedTrim);
      const hostSeed =
        (seedTrim && !seedIsSlugOnly ? seedTrim : "") ||
        (opts?.userText?.trim() &&
        !/^\/brief\b/i.test(opts.userText.trim()) &&
        !seedIsSlugOnly &&
        sanitizeProjectSlug(opts.userText.trim()) !== opts.userText.trim()
          ? opts.userText.trim()
          : "我想开始一个全新的游戏项目，请从零策划，不要沿用上一款游戏的任何设定。");
      try {
        const res = await window.gameFactory.hostChatReset(
          sessionTarget.sessionId,
          hostSeed,
          sessionTarget.instanceId,
          created.briefRel,
        );
        if (res.exitCode !== 0 || !res.data?.assistant_message) {
          if (isChatAborted(res)) {
            appendAssistant("已停止。", undefined, undefined, sessionTarget);
            return;
          }
          throw new Error(res.stderr || res.stdout || "host-chat reset failed");
        }
        applyBrainstormResult(res.data, sessionTarget);
        if (opts?.announcePath !== false) {
          setSidePanel("docs");
          appendAssistant(
            [
              `**工程已创建并绑定**：\`${created.slug}\``,
              "",
              `- 目录：\`projects/${created.slug}/\``,
              `- 顶栏已指向本工程；右侧「文档」**只列出本工程文件**`,
              `- 可先看 **工程说明**；导出 Brief 后会出现 **中文说明 · Brief**`,
              "",
              "接下来在本对话描述玩法；落实后点文档面板「导出 Brief」写入本目录。",
            ].join("\n"),
            ["描述新游戏玩法", "打开文档"],
            undefined,
            sessionTarget,
          );
        }
      } catch (e) {
        if (isAbortError(e)) {
          appendAssistant("已停止。", undefined, undefined, sessionTarget);
        } else {
          appendAssistant(
            `重置失败：${e instanceof Error ? e.message : String(e)}`,
            undefined,
            undefined,
            sessionTarget,
          );
        }
      } finally {
        clearBusy(busyId);
      }
    },
    [
      clearBriefBinding,
      activeColleague.id,
      chatStore,
      patchChatStore,
      append,
      markBusy,
      clearBusy,
      applyBrainstormResult,
      appendAssistant,
      ensureAndBindProject,
      openNewProjectModal,
    ],
  );

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
        // Session may be bound to another project — align topbar + board
        const bound = String(data?.bound_brief_rel || "").replace(/\\/g, "/");
        if (bound && !sameProjectRoot(bound, activeBriefRel)) {
          setBrief(bound);
          await syncPipelineForBriefRef.current(bound);
          setDocsFocusDiskRel(null);
          setDocsDiskRefreshKey((n) => n + 1);
        } else if (!bound && activeBriefRel && window.gameFactory?.hostChatBind) {
          // Keep topbar project: re-bind this session so docs / 视觉定稿 stay available
          await window.gameFactory.hostChatBind(sessionId, activeBriefRel);
        }
      })();
    },
    [patchChatStore, applyDraftFromPayload, activeBriefRel, setBrief],
  );

  const syncPlannerProject = useCallback(
    async (briefRel: string, sessionId?: string) => {
      if (!window.gameFactory?.hostChatBind || !briefRel) return null;
      const sid = sessionId || getActiveSession(chatStore).id;
      const res = await window.gameFactory.hostChatBind(sid, briefRel);
      if (res.exitCode !== 0) {
        appendAssistant(`策划绑定工程失败：${res.stderr || res.stdout || "bind failed"}`);
        return null;
      }
      const data = res.data;
      if (data) {
        applyDraftFromPayload(
          {
            draft_brief: data.draft_brief ?? null,
            title: data.title,
            asset_count: data.asset_count,
          },
          { replace: true },
        );
        if (data.draft_brief) setBriefDraft(data.draft_brief);
        // Pre-export Chinese mirror (skeleton, fast) whenever draft is on disk/session
        if (data.draft_brief && window.gameFactory?.hostChatZhDoc) {
          void window.gameFactory
            .hostChatZhDoc(sid, briefRel, true)
            .then((zh) => {
              if (zh.exitCode !== 0) return;
              const zhRel =
                (zh.data?.zh_doc_rel || "").replace(/\\/g, "/") ||
                `${briefRel.replace(/\/[^/]+$/i, "")}/brief.zh.md`;
              setDocsFocusDiskRel(zhRel);
              setDocsDiskRefreshKey((n) => n + 1);
            })
            .catch(() => undefined);
        }
      }
      return data;
    },
    [chatStore, appendAssistant, applyDraftFromPayload],
  );

  const handleBrainstormStart = async (seed?: string) => {
    if (activeColleague.roleKind !== "brief") return;
    const busyId = activeColleague.id;
    const sessionTarget = { instanceId: busyId, sessionId: getActiveSession(chatStore).id };
    markBusy(busyId);
    setBrainstormChoices([]);
    try {
      const res = await window.gameFactory.hostChatStart(
        sessionTarget.sessionId,
        seed,
        sessionTarget.instanceId,
        activeBriefRel,
      );
      if (res.exitCode !== 0 || !res.data?.assistant_message) {
        if (isChatAborted(res)) {
          appendAssistant("已停止。", undefined, undefined, sessionTarget);
          return;
        }
        throw new Error(res.stderr || res.stdout || "host-chat start failed");
      }
      applyBrainstormResult(res.data, sessionTarget);
    } catch (e) {
      if (isAbortError(e)) {
        appendAssistant("已停止。", undefined, undefined, sessionTarget);
      } else {
        appendAssistant(
          `Brief 对话启动失败：${e instanceof Error ? e.message : String(e)}\n\n请到 **设置 → Provider** 配置账号与 Key，或在对话里为策划实例选择 Provider；亦可确认 Pi 就绪（\`setup pi status --json\`）。`,
          undefined,
          undefined,
          sessionTarget,
        );
      }
    } finally {
      clearBusy(busyId);
    }
  };

  const handleBrainstormTurn = async (message: string) => {
    if (activeColleague.roleKind !== "brief") return;
    const busyId = activeColleague.id;
    const sessionTarget = { instanceId: busyId, sessionId: getActiveSession(chatStore).id };
    markBusy(busyId);
    setBrainstormChoices([]);
    const turnMessage = wrapVtRestyleUserMessage(vtRestyleFocusRef.current, message);
    try {
      let res = await window.gameFactory.hostChatTurn(
        sessionTarget.sessionId,
        turnMessage,
        sessionTarget.instanceId,
        activeBriefRel,
      );
      if (res.exitCode !== 0 && /Session not found/i.test(res.stderr || res.stdout || "")) {
        res = await window.gameFactory.hostChatStart(
          sessionTarget.sessionId,
          turnMessage,
          sessionTarget.instanceId,
          activeBriefRel,
        );
      }
      const data = res.data;
      if (isChatAborted(res)) {
        appendAssistant("已停止。", undefined, undefined, sessionTarget);
        return;
      }
      if (res.exitCode !== 0 || !data?.assistant_message) {
        const detail = (res.stderr || res.stdout || "").trim();
        const short =
          detail.length > 1200 ? `${detail.slice(0, 1200)}\n…` : detail || "host-chat turn failed";
        throw new Error(short);
      }
      applyBrainstormResult(data, sessionTarget);
      void refreshBrainstormStatus();
      const focus = vtRestyleFocusRef.current;
      if (focus.active && focus.kind === "restyle") {
        const reply = String(data.assistant_message || "").trim();
        if (isVtRestyleClarificationAsk(reply)) {
          appendAssistant(
            "先回答上面的澄清问题；说清楚后再点「我写好了 · 重新生成」。",
            ["生成北极星图（改选其他范围）"],
            undefined,
            sessionTarget,
          );
        } else {
          vtRestyleFocusRef.current = { ...focus, feedbackDone: true };
          setVtRestyleAwaitingText(false);
          const regen = formatVtRegenAfterFeedbackChoice(
            focus.sceneId,
            focus.sceneTitle,
          );
          appendAssistant(
            focus.sceneId
              ? `已记下你对 **${focus.sceneTitle || focus.sceneId}** 的修改意向。确认无误就点下方 **「${regen}」**。`
              : `已记下全局北极星修改意向。确认无误就点下方 **「${regen}」**。`,
            [regen, "生成北极星图（改选其他范围）"],
            undefined,
            sessionTarget,
          );
          setBrainstormChoices([regen, "生成北极星图（改选其他范围）"]);
        }
      }
    } catch (e) {
      if (isAbortError(e)) {
        appendAssistant("已停止。", undefined, undefined, sessionTarget);
      } else {
        appendAssistant(
          `回复失败：${e instanceof Error ? e.message : String(e)}`,
          undefined,
          undefined,
          sessionTarget,
        );
      }
    } finally {
      clearBusy(busyId);
    }
  };

  const handleBriefExport = async (nameHint?: string) => {
    if (activeColleague.roleKind !== "brief") {
      appendAssistant("导出 Brief 请先切换到 **策划** 同事。");
      return;
    }
    const busyId = activeColleague.id;
    const sessionTarget = { instanceId: busyId, sessionId: getActiveSession(chatStore).id };
    markBusy(busyId);
    try {
      let outputRel: string;
      let slug: string;
      if (activeBriefRel && isIsolatedBriefRel(activeBriefRel)) {
        outputRel = activeBriefRel.replace(/\\/g, "/");
        const targets = await resolvePlanTargets(outputRel);
        slug = targets.slug;
      } else {
        slug = sanitizeProjectSlug(nameHint || "") || slugifyBriefName(nameHint || draftTitle || "my-game");
        const created = await ensureAndBindProject(slug);
        if (!created) {
          throw new Error("请先创建工程（顶栏 → 新建项目），再导出 Brief。");
        }
        outputRel = created.briefRel;
        slug = created.slug;
      }
      const res = await window.gameFactory.hostChatExport(
        sessionTarget.sessionId,
        outputRel,
        sessionTarget.instanceId,
      );
      if (isChatAborted(res)) {
        appendAssistant("已停止。", undefined, undefined, sessionTarget);
        return;
      }
      if (res.exitCode !== 0) {
        throw new Error(res.stderr || res.stdout || "export failed");
      }
      const briefRel = res.data?.brief_rel || outputRel;
      setBrief(briefRel);
      await syncPipelineForBriefRef.current(briefRel);
      const extId = parseExternalBriefId(briefRel);
      const extEntry = extId ? externalEntryById[extId] : null;
      const zhRel =
        (res.data?.zh_doc_rel || "").replace(/\\/g, "/") ||
        (extId ? `${briefRel.replace(/\/brief\.json$/i, "")}/brief.zh.md` : `projects/${slug}/brief.zh.md`);
      const zhMode = res.data?.zh_doc_mode || "skeleton";
      setDocsFocusDiskRel(zhRel);
      setDocsDiskRefreshKey((n) => n + 1);
      setSidePanel("docs");
      const rootLine = extEntry
        ? `- 工程根：外置 · \`${extEntry.root_abs}\``
        : `- 工程根：\`projects/${slug}/\``;
      appendAssistant(
        `**Brief 已写入本工程**\n\n` +
          `- Brief：\`${briefRel}\`\n` +
          `- 中文说明：\`${zhRel}\`${zhMode === "llm" ? "（已翻译）" : "（中文目录骨架；配好 API Key 后重新导出可全文翻译）"}\n` +
          `${rootLine}\n\n` +
          `右侧「文档」仅显示本工程。下一步可定 **北极星图**，再交给项目经理。`,
        ["生成北极星图", "切换到项目经理", "切换到项目经理并生成流水线"],
        undefined,
        sessionTarget,
      );
    } catch (e) {
      if (isAbortError(e)) {
        appendAssistant("已停止。", undefined, undefined, sessionTarget);
      } else {
        appendAssistant(
          `导出失败：${e instanceof Error ? e.message : String(e)}`,
          undefined,
          undefined,
          sessionTarget,
        );
      }
    } finally {
      clearBusy(busyId);
    }
  };

  /** Draft → brief.zh.md before export so humans can decide whether to freeze. */
  const handleBriefZhDoc = async (opts?: { skeletonOnly?: boolean; quiet?: boolean }) => {
    if (activeColleague.roleKind !== "brief") {
      if (!opts?.quiet) appendAssistant("生成中文说明请先切换到 **策划** 同事。");
      return;
    }
    if (!window.gameFactory?.hostChatZhDoc) {
      appendAssistant("当前 GUI 不支持生成中文说明，请重启 Foundry。");
      return;
    }
    if (!activeBriefRel) {
      appendAssistant("请先绑定工程（顶栏），再生成中文说明。");
      return;
    }
    if (!briefDraft) {
      appendAssistant("还没有工作草稿。先和策划聊几轮，或绑定带有 brief.draft.json 的工程。");
      return;
    }
    const busyId = activeColleague.id;
    const sessionTarget = { instanceId: busyId, sessionId: getActiveSession(chatStore).id };
    if (!opts?.quiet) markBusy(busyId);
    try {
      const res = await window.gameFactory.hostChatZhDoc(
        sessionTarget.sessionId,
        activeBriefRel,
        Boolean(opts?.skeletonOnly),
      );
      if (res.exitCode !== 0) {
        throw new Error(res.stderr || res.stdout || "zh-doc failed");
      }
      const zhRel =
        (res.data?.zh_doc_rel || "").replace(/\\/g, "/") ||
        `${activeBriefRel.replace(/\/[^/]+$/i, "")}/brief.zh.md`;
      const zhMode = res.data?.zh_doc_mode || "skeleton";
      setDocsFocusDiskRel(zhRel);
      setDocsDiskRefreshKey((n) => n + 1);
      setSidePanel("docs");
      if (!opts?.quiet) {
        appendAssistant(
          `**中文说明已更新**（导出前审阅）\n\n` +
            `- \`${zhRel}\`${zhMode === "llm" ? "（全文翻译）" : "（中文目录骨架）"}\n` +
            `- 看完再决定是否「导出 Brief」冻结。`,
          ["打开文档", "导出 Brief"],
          undefined,
          sessionTarget,
        );
      }
    } catch (e) {
      if (!opts?.quiet) {
        appendAssistant(
          `生成中文说明失败：${e instanceof Error ? e.message : String(e)}`,
          undefined,
          undefined,
          sessionTarget,
        );
      }
    } finally {
      if (!opts?.quiet) clearBusy(busyId);
    }
  };

  const handleBriefUiWireframe = async () => {
    if (activeColleague.roleKind !== "brief") {
      appendAssistant("生成 UI 示意请先切换到 **策划** 同事。");
      return;
    }
    if (!window.gameFactory?.hostChatUiWireframe) {
      appendAssistant("当前 GUI 不支持生成 UI 示意，请重启 Foundry。");
      return;
    }
    if (!activeBriefRel) {
      appendAssistant("请先绑定工程（顶栏），再生成 UI 示意。");
      return;
    }
    if (!briefDraft) {
      appendAssistant("还没有工作草稿。先和策划聊几轮，或绑定带有 brief.draft.json 的工程。");
      return;
    }
    const busyId = activeColleague.id;
    const sessionTarget = { instanceId: busyId, sessionId: getActiveSession(chatStore).id };
    markBusy(busyId);
    append("log", "生成 UI 示意：从 draft ui_panels 写入 ui-wireframe.md…", undefined, sessionTarget);
    try {
      const res = await window.gameFactory.hostChatUiWireframe(
        sessionTarget.sessionId,
        activeBriefRel,
      );
      const data = res.data;
      if (!data?.ok) {
        const msg =
          data?.error ||
          (res.exitCode !== 0 ? res.stderr || res.stdout : "") ||
          "ui-wireframe failed";
        throw new Error(msg.trim() || "生成 UI 示意失败");
      }
      const wireRel =
        (data.ui_wireframe_rel || "").replace(/\\/g, "/") ||
        `${activeBriefRel.replace(/\/[^/]+$/i, "")}/ui-wireframe.md`;
      const panelCount = data.panel_count ?? 0;
      setDocsFocusDiskRel(wireRel);
      setDocsDiskRefreshKey((n) => n + 1);
      setSidePanel("docs");
      appendAssistant(
        `**UI 示意已生成**\n\n` +
          `- \`${wireRel}\`（${panelCount} 个面板）\n` +
          `- 程序员侧栏文档中可查阅字符线稿。`,
        ["打开文档"],
        undefined,
        sessionTarget,
      );
    } catch (e) {
      appendAssistant(
        `生成 UI 示意失败：${e instanceof Error ? e.message : String(e)}`,
        undefined,
        undefined,
        sessionTarget,
      );
    } finally {
      clearBusy(busyId);
    }
  };

  const handleBriefAutofix = async (maxRounds = 5) => {
    if (activeColleague.roleKind !== "brief") {
      appendAssistant("自动修 Brief 请先切换到 **策划** 同事。");
      return;
    }
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
      const res = await window.gameFactory.hostChatAutofix(
        sessionTarget.sessionId,
        maxRounds,
        sessionTarget.instanceId,
      );
      const data = res.data;
      if (isChatAborted(res)) {
        appendAssistant("已停止。", undefined, undefined, sessionTarget);
        return;
      }
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
          `**自动修完成**：结构校验已通过（用了 ${data.rounds_run ?? 0} 轮）。可点「保存 Brief」；制作审查为可选，不挡导出。`,
          ["保存 Brief"],
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
      if (isAbortError(e)) {
        appendAssistant("已停止。", undefined, undefined, sessionTarget);
      } else {
        appendAssistant(
          `自动修失败：${e instanceof Error ? e.message : String(e)}`,
          undefined,
          undefined,
          sessionTarget,
        );
      }
    } finally {
      clearBusy(busyId);
    }
  };

  const handleBriefMakeability = async () => {
    if (activeColleague.roleKind !== "brief") {
      appendAssistant("制作审查请先切换到 **策划** 同事。");
      return;
    }
    if (!window.gameFactory?.hostChatMakeability) {
      appendAssistant("当前 GUI 不支持制作审查，请重启 Foundry。");
      return;
    }
    const busyId = activeColleague.id;
    const sessionTarget = { instanceId: busyId, sessionId: getActiveSession(chatStore).id };
    markBusy(busyId);
    append(
      "log",
      "制作审查：独立子 LLM 审查 draft brief 的制作完备性…",
      undefined,
      sessionTarget,
    );
    try {
      const res = await window.gameFactory.hostChatMakeability(
        sessionTarget.sessionId,
        sessionTarget.instanceId,
      );
      const data = res.data;
      if (isChatAborted(res)) {
        appendAssistant("已停止。", undefined, undefined, sessionTarget);
        return;
      }
      if (!data) {
        throw new Error(res.stderr || res.stdout || "makeability failed");
      }
      let content = data.assistant_message || "制作审查完成。";
      const intentGaps = data.review?.intent_gaps || [];
      const repairGaps = data.review?.repair_gaps || [];
      const hasIntent = intentGaps.some((g) => String(g?.id || "").trim());
      const hasRepair = repairGaps.some((g) => String(g?.id || "").trim());
      const repairAnswers = (data.review?.repair_answers || []).map((row) => ({
        gap_id: String(row.gap_id || ""),
        ...(row.choice ? { choice: String(row.choice) } : {}),
        ...(row.note ? { note: String(row.note) } : {}),
      }));
      const head = (data.assistant_message || "制作审查完成。").split("\n\n")[0];

      // Intent and repair can both exist — emit separate cards so neither is hidden (M1).
      if (hasRepair) {
        appendAssistant(
          hasIntent
            ? `${head}\n\n下方卡片可「重试写入」已保存但验证失败的答案。`
            : `${head}\n\n下方卡片可「重试写入」已保存的答案（无需重新选题）。`,
          undefined,
          undefined,
          sessionTarget,
          {
            status: "repair_failed" as const,
            review: {
              ...(data.review || {}),
              intent_gaps: repairGaps,
            },
            lastAnswers: repairAnswers,
          },
        );
      }
      if (hasIntent) {
        appendAssistant(
          `${head}\n\n下方 **制作审查 · Critic** 卡片中点选选项并「写入草稿」。`,
          undefined,
          undefined,
          sessionTarget,
          {
            status: "pending" as const,
            review: data.review || { intent_gaps: intentGaps },
          },
        );
      }
      if (!hasIntent && !hasRepair) {
        appendAssistant(content, undefined, undefined, sessionTarget);
      }
      applyDraftFromPayload(
        {
          ...data,
          draft_brief: data.draft_brief ?? briefDraft,
          gaps: Array.isArray(data.gaps) ? data.gaps : briefDraftStatus?.gaps,
        },
        { replace: true },
      );
      if (data.draft_brief) setBriefDraft(data.draft_brief);
      setBrainstormReady(Boolean(data.ready_to_export));
      void refreshBrainstormStatus();
    } catch (e) {
      if (isAbortError(e)) {
        appendAssistant("已停止。", undefined, undefined, sessionTarget);
      } else {
        appendAssistant(
          `制作审查失败：${e instanceof Error ? e.message : String(e)}`,
          undefined,
          undefined,
          sessionTarget,
        );
      }
    } finally {
      clearBusy(busyId);
    }
  };

  const handleMakeabilityAnswer = async (
    messageId: string,
    answers: import("./components/MakeabilityGapCard").MakeabilityGapAnswer[],
  ) => {
    if (activeColleague.roleKind !== "brief") {
      appendAssistant("审查缺口写入请先切换到 **策划** 同事。");
      return;
    }
    if (!window.gameFactory?.hostChatMakeabilityAnswer) {
      appendAssistant("当前 GUI 不支持审查缺口写入，请重启 Foundry。");
      return;
    }
    if (!answers.length) return;
    const busyId = activeColleague.id;
    const sessionTarget = { instanceId: busyId, sessionId: getActiveSession(chatStore).id };
    markBusy(busyId);
    append(
      "log",
      `制作审查：将 ${answers.length} 条选项写入草稿…`,
      undefined,
      sessionTarget,
    );
    const localPatch = makeabilityCardLocalSubmitPatch(answers);
    patchChatStore((prev) =>
      updateSessionMessages(prev, sessionTarget.instanceId, sessionTarget.sessionId, (msgs) =>
        msgs.map((m) =>
          m.id === messageId && m.makeabilityCard
            ? {
                ...m,
                makeabilityCard: {
                  ...m.makeabilityCard,
                  ...localPatch,
                },
              }
            : m,
        ),
      ),
    );
    try {
      const res = await window.gameFactory.hostChatMakeabilityAnswer(
        sessionTarget.sessionId,
        answers,
        sessionTarget.instanceId,
      );
      const data = res.data;
      if (isChatAborted(res)) {
        appendAssistant("已停止。", undefined, undefined, sessionTarget);
        return;
      }
      if (!data) {
        throw new Error(res.stderr || res.stdout || "makeability-answer failed");
      }
      const serverPatch = makeabilityCardAfterServerPatch(data, answers);
      patchChatStore((prev) =>
        updateSessionMessages(prev, sessionTarget.instanceId, sessionTarget.sessionId, (msgs) =>
          msgs.map((m) =>
            m.id === messageId && m.makeabilityCard
              ? {
                  ...m,
                  makeabilityCard: {
                    ...m.makeabilityCard,
                    ...serverPatch,
                    review: data.review ?? m.makeabilityCard.review,
                  },
                }
              : m,
          ),
        ),
      );
      appendAssistant(
        data.assistant_message || "已按审查选项写入工作草稿。请再点一次「审」确认意图缺口清空。",
        undefined,
        undefined,
        sessionTarget,
      );
      applyDraftFromPayload(
        {
          ...data,
          draft_brief: data.draft_brief ?? briefDraft,
          gaps: Array.isArray(data.gaps) ? data.gaps : briefDraftStatus?.gaps,
        },
        { replace: true },
      );
      if (data.draft_brief) setBriefDraft(data.draft_brief);
      setBrainstormReady(false);
      void refreshBrainstormStatus();
    } catch (e) {
      if (isAbortError(e)) {
        appendAssistant("已停止。", undefined, undefined, sessionTarget);
      } else {
        appendAssistant(
          `审查写入失败：${e instanceof Error ? e.message : String(e)}`,
          undefined,
          undefined,
          sessionTarget,
        );
      }
    } finally {
      clearBusy(busyId);
    }
  };

  const handleBriefEnrich = async () => {
    if (activeColleague.roleKind !== "brief") {
      appendAssistant("补全细节请先切换到 **策划** 同事。");
      return;
    }
    if (!window.gameFactory?.hostChatEnrich) {
      appendAssistant("当前 GUI 不支持补全细节，请重启 Foundry。");
      return;
    }
    const hint =
      typeof window.prompt === "function"
        ? window.prompt("补全要求（可留空=整稿加厚）", "")
        : "";
    if (hint === null) return;
    const busyId = activeColleague.id;
    const sessionTarget = { instanceId: busyId, sessionId: getActiveSession(chatStore).id };
    markBusy(busyId);
    append(
      "log",
      hint.trim()
        ? `补全细节：按要求「${hint.trim()}」加厚 draft…`
        : "补全细节：开放式加厚 draft（玩家可见流程/呈现/参数名）…",
      undefined,
      sessionTarget,
    );
    try {
      const res = await window.gameFactory.hostChatEnrich(
        sessionTarget.sessionId,
        hint.trim() || null,
        sessionTarget.instanceId,
      );
      if (isChatAborted(res)) {
        appendAssistant("已停止。", undefined, undefined, sessionTarget);
        return;
      }
      if (res.exitCode !== 0 && !res.data?.ok) {
        throw new Error(res.stderr || res.stdout || "enrich failed");
      }
      const data = res.data;
      if (!data) {
        throw new Error(res.stderr || res.stdout || "enrich failed");
      }
      appendAssistant(
        data.assistant_message || "Brief 细节已加厚。",
        ["制作审查", "议题头脑风暴"],
        undefined,
        sessionTarget,
      );
      applyDraftFromPayload(
        {
          ...data,
          draft_brief: data.draft_brief ?? briefDraft,
          gaps: Array.isArray(data.gaps) ? data.gaps : briefDraftStatus?.gaps,
        },
        { replace: true },
      );
      if (data.draft_brief) setBriefDraft(data.draft_brief);
      setBrainstormReady(Boolean(data.ready_to_export));
      void refreshBrainstormStatus();
    } catch (e) {
      if (isAbortError(e)) {
        appendAssistant("已停止。", undefined, undefined, sessionTarget);
      } else {
        appendAssistant(
          `补全失败：${e instanceof Error ? e.message : String(e)}`,
          undefined,
          undefined,
          sessionTarget,
        );
      }
    } finally {
      clearBusy(busyId);
    }
  };

  const handleTopicBrainstorm = async () => {
    if (activeColleague.roleKind !== "brief") {
      appendAssistant("议题头脑风暴请先切换到 **策划** 同事。");
      return;
    }
    if (!window.gameFactory?.hostChatTopicBrainstorm) {
      appendAssistant("当前 GUI 不支持议题头脑风暴，请重启 Foundry。");
      return;
    }
    const topic =
      typeof window.prompt === "function"
        ? window.prompt("要头脑风暴的议题（例如：拉线张力怎么呈现）", "")
        : "";
    if (topic === null || !String(topic).trim()) return;
    const busyId = activeColleague.id;
    const sessionTarget = { instanceId: busyId, sessionId: getActiveSession(chatStore).id };
    markBusy(busyId);
    append("log", `议题头脑风暴：${String(topic).trim()}…`, undefined, sessionTarget);
    try {
      const res = await window.gameFactory.hostChatTopicBrainstorm(
        sessionTarget.sessionId,
        String(topic).trim(),
        null,
        false,
        sessionTarget.instanceId,
      );
      if (isChatAborted(res)) {
        appendAssistant("已停止。", undefined, undefined, sessionTarget);
        return;
      }
      if (res.exitCode !== 0 && !res.data?.ok) {
        throw new Error(res.stderr || res.stdout || "brainstorm failed");
      }
      const data = res.data || {};
      const proposals = data.brainstorm_result?.proposals || [];
      const lines = proposals.map(
        (p) =>
          `- **${p.id}**（${p.role}）**${p.title}**\n  ${(p.bullets || []).map((b) => `· ${b}`).join("\n  ")}`,
      );
      const choices = proposals
        .map((p) => (p.id && p.title ? `采用 ${p.id}：${p.title}` : ""))
        .filter(Boolean);
      if (proposals.length >= 2) {
        choices.push("融合前两个方案");
      }
      appendAssistant(
        (data.assistant_message || "头脑风暴完成。") +
          (lines.length ? `\n\n${lines.join("\n")}` : ""),
        choices.length ? choices : undefined,
        undefined,
        sessionTarget,
      );
    } catch (e) {
      if (isAbortError(e)) {
        appendAssistant("已停止。", undefined, undefined, sessionTarget);
      } else {
        appendAssistant(
          `头脑风暴失败：${e instanceof Error ? e.message : String(e)}`,
          undefined,
          undefined,
          sessionTarget,
        );
      }
    } finally {
      clearBusy(busyId);
    }
  };

  const handleBrainstormApply = async (proposalIds: string[], fuse = false) => {
    if (activeColleague.roleKind !== "brief") {
      appendAssistant("采用头脑风暴方案请先切换到 **策划** 同事。");
      return;
    }
    if (!window.gameFactory?.hostChatBrainstormApply) {
      appendAssistant("当前 GUI 不支持采用头脑风暴方案，请重启 Foundry。");
      return;
    }
    const busyId = activeColleague.id;
    const sessionTarget = { instanceId: busyId, sessionId: getActiveSession(chatStore).id };
    markBusy(busyId);
    append(
      "log",
      fuse
        ? `融合方案 ${proposalIds.join(",")} 并写回 draft…`
        : `采用方案 ${proposalIds.join(",")} 并写回 draft…`,
      undefined,
      sessionTarget,
    );
    try {
      const res = await window.gameFactory.hostChatBrainstormApply(
        sessionTarget.sessionId,
        proposalIds,
        fuse,
        sessionTarget.instanceId,
      );
      if (isChatAborted(res)) {
        appendAssistant("已停止。", undefined, undefined, sessionTarget);
        return;
      }
      if (res.exitCode !== 0 && !res.data?.ok) {
        throw new Error(res.stderr || res.stdout || "brainstorm-apply failed");
      }
      const data = res.data;
      if (!data) {
        throw new Error(res.stderr || res.stdout || "brainstorm-apply failed");
      }
      appendAssistant(
        data.assistant_message || "方案已写回 draft。",
        ["制作审查", "补全细节"],
        undefined,
        sessionTarget,
      );
      applyDraftFromPayload(
        {
          ...data,
          draft_brief: data.draft_brief ?? briefDraft,
          gaps: Array.isArray(data.gaps) ? data.gaps : briefDraftStatus?.gaps,
        },
        { replace: true },
      );
      if (data.draft_brief) setBriefDraft(data.draft_brief);
      setBrainstormReady(Boolean(data.ready_to_export));
      void refreshBrainstormStatus();
    } catch (e) {
      if (isAbortError(e)) {
        appendAssistant("已停止。", undefined, undefined, sessionTarget);
      } else {
        appendAssistant(
          `采用方案失败：${e instanceof Error ? e.message : String(e)}`,
          undefined,
          undefined,
          sessionTarget,
        );
      }
    } finally {
      clearBusy(busyId);
    }
  };

  const handleAgentTurn = async (
    message: string,
    opts?: { instanceId?: string },
  ) => {
    if (agentConfigSavingRef.current) return;
    const colleague =
      (opts?.instanceId
        ? chatStore.roster.find((c) => c.id === opts.instanceId)
        : null) || activeColleague;
    const role = colleague.roleKind;
    if (!isAgentChatRole(role)) {
      return;
    }
    const sessionId =
      (opts?.instanceId
        ? chatStore.activeByInstance[colleague.id] ||
          chatStore.sessions.find((s) => s.instanceId === colleague.id)?.id
        : null) || activeSession.id;
    if (!sessionId) return;
    if (opts?.instanceId && opts.instanceId !== activeColleague.id) {
      patchChatStore((prev) => setActiveInstance(prev, opts.instanceId!));
    }
    const target = {
      instanceId: colleague.id,
      sessionId,
      role,
      displayName: colleague.displayName,
    };
    markBusy(target.instanceId);
    setAgentActionChoices([]);
    const programmers = chatStore.roster.filter((c) => c.roleKind === "programmer");
    const defaultTarget =
      programmers.find((c) => c.id === target.instanceId)?.id || programmers[0]?.id;
    const waitHint =
      role === "it"
        ? "IT 首轮可能较慢（约 1–2 分钟属正常）。"
        : role === "advisor"
          ? "顾问只读咨询，通常几十秒内回复。"
          : "Hermes / Codex 常需 1–3 分钟才回完整答复。";
    append(
      "log",
      `「${target.displayName}」执行器运行中…\n（右侧可开「看板」；下方会显示等待秒数。${waitHint}）`,
      undefined,
      target,
    );
    const agentStartedAt = Date.now();
    const heartbeat = window.setInterval(() => {
      const secs = Math.floor((Date.now() - agentStartedAt) / 1000);
      patchChatStore((store) =>
        updateSessionMessages(store, target.instanceId, target.sessionId, (prev) => {
          const awaitingApproval =
            prev.some((m) => m.toolPermission?.status === "pending") ||
            pendingToolPermissionsRef.current.some(
              (p) =>
                (!p.instanceId || p.instanceId === target.instanceId) &&
                (!p.sessionId || p.sessionId === target.sessionId),
            );
          let idx = -1;
          for (let i = prev.length - 1; i >= 0; i -= 1) {
            const m = prev[i];
            if (m?.role === "log" && String(m.content || "").includes("执行器运行中")) {
              idx = i;
              break;
            }
          }
          if (idx < 0) return prev;
          const last = prev[idx];
          const base =
            last.content.split("\n")[0] || `「${target.displayName}」执行器运行中…`;
          const statusLine = awaitingApproval
            ? `…已挂起：请在对话里的批准卡片上点「允许」或「拒绝」（${secs}s）`
            : `…仍在运行 ${secs}s（计时跳动即正常；${waitHint}）`;
          const updated = {
            ...last,
            content: `${base}\n${statusLine}`,
          };
          return [...prev.slice(0, idx), updated, ...prev.slice(idx + 1)];
        }),
      );
    }, 4000);
    try {
      if (!window.gameFactory?.agentTurn) {
        throw new Error("agentTurn IPC 不可用，请重启 GUI。");
      }
      const progressRel = activeBriefRel
        ? (await resolvePlanTargets(activeBriefRel)).progressRel
        : undefined;
      let piSessionTrust: boolean | undefined;
      if (target.role === "it") {
        const mem = itSessionTrustRef.current[target.instanceId];
        if (typeof mem === "boolean") {
          piSessionTrust = mem;
        } else if (window.gameFactory?.getConfig) {
          try {
            const cfg = await window.gameFactory.getConfig();
            const data = (cfg?.data || {}) as Record<string, unknown>;
            const instances = loadAgentInstancesFromConfig(data);
            const rec = instances[target.instanceId];
            piSessionTrust =
              typeof rec?.pi_session_trust === "boolean" ? rec.pi_session_trust : true;
          } catch {
            piSessionTrust = true;
          }
        } else {
          piSessionTrust = true;
        }
      }
      const res = await window.gameFactory.agentTurn({
        role: target.role,
        sessionId: target.sessionId,
        message,
        executor: colleague.executor || undefined,
        brief: activeBriefRel || undefined,
        progress: progressRel,
        instanceId: target.instanceId,
        targetInstanceId: target.role === "product_host" ? defaultTarget : undefined,
        rosterJson:
          target.role === "product_host"
            ? JSON.stringify(
                programmers.map((c) => ({ id: c.id, display_name: c.displayName })),
              )
            : undefined,
        piSessionTrust,
      });
      const data = res.data;
      if (isChatAborted(res)) {
        append("assistant", "已停止。", undefined, target);
        return;
      }
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
      const prepared = prepareAgentDisplay(rawReply, { role: target.role });
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
          const proj = (await resolvePlanTargets(activeBriefRel)).godotProjectRel;
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
      if (isAbortError(e)) {
        append("assistant", "已停止。", undefined, target);
      } else {
        append(
          "assistant",
          `「${target.displayName}」回复失败：${e instanceof Error ? e.message : String(e)}\n\n` +
            (target.role === "it"
              ? String(e instanceof Error ? e.message : e).includes("9009")
                ? "Windows **exit 9009** 通常是找不到内嵌 Python（CLI 起不来），与 DeepSeek Key 无关。请改用最新安装包，或确认安装目录 `resources/python/Scripts/python.exe` 存在；勿只依赖系统 PATH 上的 `python`。"
                : "IT 默认使用**内置 Pi**，也可切到 Codex / Cursor。若当前是 Pi，请确认：① 已用 Electron 39+（`npm install`）；② **设置 → Agent · Pi** / 实例 Provider+Key；③ `setup pi status --json` 显示 ready。"
              : "请到 **设置 → 环境** 确认执行器 CLI 已安装并登录（Hermes / Codex / Cursor Agent），并在 **设置 → Agent** 或对话配置里为当前实例选择执行器。"),
          undefined,
          target,
          target.role === "product_host"
            ? ["生成流水线", "运行资产生成（含文案）", "打开看板"]
            : undefined,
        );
      }
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

  /** Prefer pipeline meta.output_dir only when it belongs to the active project. */
  useEffect(() => {
    let cancelled = false;
    void (async () => {
      if (selectedManifest && activeBriefRel) {
        try {
          const meta = await window.gameFactory.getManifestMeta(selectedManifest);
          const metaBrief = String(meta?.brief || "").replace(/\\/g, "/");
          if (metaBrief && !sameProjectRoot(metaBrief, activeBriefRel)) {
            /* stale manifest from another project — fall through to brief path */
          } else {
            const out = String(meta?.output_dir || "")
              .replace(/\\/g, "/")
              .replace(/\/$/, "");
            if (out) {
              if (!cancelled) setAssetsManifestRel(`${out}/assets-manifest.json`);
              return;
            }
          }
        } catch {
          /* fall through */
        }
      }
      if (activeBriefRel) {
        const out = (await resolvePlanTargets(activeBriefRel)).outputDirRel.replace(/\/$/, "");
        if (!cancelled) setAssetsManifestRel(`${out}/assets-manifest.json`);
        return;
      }
      if (!cancelled) setAssetsManifestRel(null);
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedManifest, activeBriefRel, resolvePlanTargets]);

  /** Clear then load pipeline/board/assets for a brief. Always prefer projects/<slug>/pipeline. */
  const syncPipelineForBrief = useCallback(
    async (briefRel: string | null) => {
      setSelectedManifest("");
      setTasks([]);
      setStatus(null);
      setAssetsManifestRel(null);
      setLogs([]);
      runWithoutVtWarned.current = false;
      if (!briefRel) return null;
      const normalized = briefRel.replace(/\\/g, "/");
      const preferred = (await resolvePlanTargets(normalized)).manifestRel;
      const manifests = await window.gameFactory.listManifests();
      const byBrief =
        window.gameFactory.findManifestForBrief
          ? await window.gameFactory.findManifestForBrief(normalized)
          : null;
      let manifest = "";
      if (manifests.some((m) => m.path === preferred)) {
        manifest = preferred;
      } else if (byBrief?.path && manifests.some((m) => m.path === byBrief.path)) {
        const metaBrief = String(byBrief.meta?.brief || "").replace(/\\/g, "/");
        if (!metaBrief || sameProjectRoot(metaBrief, normalized)) {
          manifest = byBrief.path;
        }
      }
      if (manifest) {
        setSelectedManifest(manifest);
        await refreshManifest(manifest);
      }
      return manifest || null;
    },
    [refreshManifest, resolvePlanTargets],
  );
  syncPipelineForBriefRef.current = syncPipelineForBrief;

  const switchProject = useCallback(
    async (briefRel: string) => {
      const normalized = briefRel.replace(/\\/g, "/");
      setBrief(normalized);
      const targets = await resolvePlanTargets(normalized);
      const slug = targets.slug;
      // Bind every brief colleague session so planner always knows the project
      const briefIds = chatStore.roster
        .filter((c) => c.roleKind === "brief")
        .map((c) => chatStore.activeByInstance[c.id])
        .filter(Boolean) as string[];
      if (briefIds.length === 0 && agentRole === "brief") {
        await syncPlannerProject(normalized);
      } else {
        for (const sid of briefIds) {
          await syncPlannerProject(normalized, sid);
        }
      }
      const manifest = await syncPipelineForBrief(normalized);
      setDocsFocusDiskRel(null);
      setDocsDiskRefreshKey((n) => n + 1);
      let briefStatus: "ready" | "draft" | "unknown" = "unknown";
      try {
        const briefs = window.gameFactory?.listBriefs
          ? await window.gameFactory.listBriefs()
          : [];
        const hit = (briefs || []).find(
          (b) => String(b.path || "").replace(/\\/g, "/") === normalized,
        );
        if (hit?.status === "draft" || hit?.status === "ready") briefStatus = hit.status;
      } catch {
        /* keep unknown */
      }
      const draftRel = normalized.replace(/\/brief\.json$/i, "/brief.draft.json");
      const briefLine =
        briefStatus === "draft"
          ? `工作草稿：\`${draftRel}\`（**尚未导出** \`brief.json\`，列表里的路径只是工程键）`
          : briefStatus === "ready"
            ? `Brief：\`${normalized}\`（已导出）`
            : `工程键：\`${normalized}\``;
      const pipeLine = manifest
        ? `\n看板：\`${manifest}\``
        : briefStatus === "draft"
          ? "\n（尚无流水线 — 先在文档里审阅/导出 Brief，再让项目经理生成流水线）"
          : "\n（尚无 pipeline manifest — 看板已清空；可让项目经理生成流水线）";
      append(
        "assistant",
        `已切换到工程 **${slug}**\n\n${briefLine}${pipeLine}`,
        undefined,
        undefined,
        briefStatus === "draft"
          ? ["打开文档", "生成中文说明"]
          : ["打开文档", "生成流水线"],
      );
    },
    [
      setBrief,
      syncPipelineForBrief,
      syncPlannerProject,
      append,
      agentRole,
      chatStore.roster,
      chatStore.activeByInstance,
      resolvePlanTargets,
    ],
  );

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
    await refreshExternalProjects();
    const env = await refreshEnv();
    await refreshHandoffs();

    const briefs = await window.gameFactory.listBriefs();
    // unset → first-run fallback; none → restore last real selection (never leave docs empty)
    const pref = readActiveBriefPreference();
    let brief: string | null = null;
    if (pref.kind === "brief") {
      brief = pref.rel;
    } else if (pref.kind === "unset") {
      brief = briefs[0]?.path || null;
    } else {
      // pref.kind === "none": prefer lastBrief, then session bind, then newest listed brief.
      // Avoid sticking on 「未选择工程」so docs disk list (工程说明 / brief.zh.md …) stays available.
      brief = loadLastBriefRel();
      if (!brief) {
        try {
          const store = loadSessionStore();
          for (const c of store.roster) {
            if (c.roleKind !== "brief") continue;
            const sid = store.activeByInstance[c.id];
            if (!sid || !window.gameFactory?.hostChatStatus) continue;
            const st = await window.gameFactory.hostChatStatus(sid);
            const bound = String(st.data?.bound_brief_rel || "").replace(/\\/g, "/");
            if (bound) {
              brief = bound;
              break;
            }
          }
        } catch {
          /* stay null */
        }
      }
      if (!brief) {
        brief = briefs[0]?.path || null;
      }
    }
    if (brief) {
      setBrief(brief);
      setDocsDiskRefreshKey((n) => n + 1);
      // Re-bind active planner session so draft + docs stay scoped to this project
      try {
        const store = loadSessionStore();
        const colleague = getActiveColleague(store);
        if (colleague?.roleKind === "brief") {
          const sid = store.activeByInstance[colleague.id] || getActiveSession(store).id;
          if (sid && window.gameFactory?.hostChatBind) {
            const res = await window.gameFactory.hostChatBind(sid, brief);
            const data = res?.data;
            if (data?.draft_brief) {
              applyDraftFromPayload(
                {
                  draft_brief: data.draft_brief ?? null,
                  title: data.title,
                  asset_count: data.asset_count,
                },
                { replace: true },
              );
              setBriefDraft(data.draft_brief);
            }
          }
        }
      } catch {
        /* bind best-effort */
      }
    } else {
      setActiveBriefRel(null);
      setSelectedManifest("");
      setTasks([]);
      setStatus(null);
      setAssetsManifestRel(null);
      setVisualReferenceReady(false);
    }

    if (brief) {
      await syncPipelineForBrief(brief);
      await refreshVisualTarget(brief);
    } else {
      await syncPipelineForBrief(null);
    }

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
          setSidePanel(null);
          openSettings("env");
        }
      }
    }
  }, [refreshEnv, refreshHandoffs, refreshVisualTarget, append, setBrief, syncPipelineForBrief, refreshExternalProjects, openSettings, applyDraftFromPayload]);

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

  const didMountLoad = useRef(false);
  useEffect(() => {
    // Mount-only: must not re-run when activeBriefRel clears, or listBriefs()[0] used to rebind 黑哨.
    if (didMountLoad.current) return;
    didMountLoad.current = true;
    void loadInitial()
      .then(() => refreshBrainstormStatus())
      .catch((e) =>
        append("system", `初始化失败：${e instanceof Error ? e.message : String(e)}`),
      );
  }, [loadInitial, append, refreshBrainstormStatus]);

  // IPC listeners must NOT share the didMountLoad early-return: dep changes / HMR
  // would remove listeners in cleanup and never re-subscribe — permission cards vanish.
  useEffect(() => {
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
    const offPermission = window.gameFactory?.onToolPermission?.((payload) => {
      const sid = String(payload.sessionId || "").trim();
      const instanceId = String(payload.instanceId || "").trim();
      const permissionId = String(payload.permissionId || "");
      if (!permissionId) return;
      console.info("[gui] tool-permission received", {
        permissionId,
        sid,
        instanceId,
        source: payload.source,
      });
      const isCursorAcp = payload.source === "cursor_acp";
      const isHermesAcp = payload.source === "hermes_acp";
      const isCodexAppServer = payload.source === "codex_app_server";
      const source = isCursorAcp
        ? ("cursor_acp" as const)
        : isHermesAcp
          ? ("hermes_acp" as const)
          : isCodexAppServer
            ? ("codex_app_server" as const)
            : undefined;

      // Resolve target session first so we never leave orphan pending without a card.
      const storeSnap = chatStoreRef.current;
      const hit = sid ? storeSnap.sessions.find((s) => s.id === sid) : undefined;
      const byInstance =
        !hit && instanceId
          ? storeSnap.sessions.find(
              (s) =>
                s.instanceId === instanceId &&
                s.id === (storeSnap.activeByInstance[instanceId] || ""),
            ) || storeSnap.sessions.find((s) => s.instanceId === instanceId)
          : undefined;
      const target = hit
        ? { instanceId: hit.instanceId, sessionId: hit.id }
        : byInstance
          ? { instanceId: byInstance.instanceId, sessionId: byInstance.id }
          : {
              instanceId: storeSnap.activeInstanceId,
              sessionId: storeSnap.activeByInstance[storeSnap.activeInstanceId] || "",
            };
      if (!target.sessionId) {
        console.warn("[gui] tool-permission dropped — no sessionId target", payload);
        void window.gameFactory?.decideToolPermission?.(permissionId, "deny").catch(() => {
          /* bridge may already be gone */
        });
        return;
      }

      setPendingToolPermissions((prev) => {
        if (prev.some((p) => p.permissionId === permissionId)) return prev;
        return [
          ...prev,
          {
            permissionId,
            sessionId: sid || target.sessionId,
            instanceId: instanceId || target.instanceId,
            turnId: payload.turnId,
            argvSummary: String(payload.argvSummary || ""),
            source,
          },
        ];
      });
      patchChatStore((store) => {
        const title = isCursorAcp
          ? "Cursor 需要批准"
          : isHermesAcp
            ? "Hermes 需要批准"
            : isCodexAppServer
              ? "Codex 需要批准"
              : "需要批准的变更";
        const msg: ChatMessage = {
          id: newMessageId(),
          role: "system",
          content: title,
          timestamp: Date.now(),
          toolPermission: {
            permissionId,
            sessionId: sid || target.sessionId,
            turnId: payload.turnId,
            argvSummary: String(payload.argvSummary || ""),
            status: "pending",
            ...(source ? { source } : {}),
          },
        };
        return updateSessionMessages(store, target.instanceId, target.sessionId, (msgs) => {
          if (msgs.some((m) => m.toolPermission?.permissionId === permissionId)) return msgs;
          return [...msgs, msg];
        });
      });
    });
    const offPermissionResolved = window.gameFactory?.onToolPermissionResolved?.((payload) => {
      const permissionId = String(payload.permissionId || "");
      if (!permissionId) return;
      const decision = String(payload.decision || "deny");
      const statusMap = {
        once: "allowed_once",
        turn: "allowed_turn",
        session: "allowed_session",
        deny: "denied",
      } as const;
      const status = statusMap[decision as keyof typeof statusMap] || "denied";
      setPendingToolPermissions((prev) => prev.filter((p) => p.permissionId !== permissionId));
      patchChatStore((store) => ({
        ...store,
        sessions: store.sessions.map((s) => ({
          ...s,
          messages: s.messages.map((m) =>
            m.toolPermission?.permissionId === permissionId &&
            m.toolPermission.status === "pending"
              ? {
                  ...m,
                  toolPermission: {
                    ...m.toolPermission,
                    status,
                  },
                }
              : m,
          ),
        })),
      }));
    });
    return () => {
      off?.();
      offToolchain?.();
      offPermission?.();
      offPermissionResolved?.();
    };
  }, [patchChatStore]);

  const handlePipelinePmHeal = async () => {
    if (!selectedManifest) {
      append("assistant", "没有流水线 manifest，无法处理失败任务。");
      return;
    }
    const busyId = activeColleague.id;
    markBusy(busyId);
    try {
      const diag = window.gameFactory.pipelineDiagnose
        ? await window.gameFactory.pipelineDiagnose(selectedManifest)
        : null;
      const advice = formatPmFitAdvice(diag?.data);
      const heal = window.gameFactory.pipelineHeal
        ? await window.gameFactory.pipelineHeal(selectedManifest, true)
        : null;
      const healed = (heal?.data?.healed as string[] | undefined) || [];
      const needs = (diag?.data?.needs_hermes as DiagnoseItem[] | undefined) || [];
      await refreshManifest(selectedManifest);

      append(
        "assistant",
        `**是否适合项目经理处理：${advice.headline}**\n\n${advice.detail}`,
        undefined,
        undefined,
        advice.suitable
          ? undefined
          : ["运行资产生成", "打开看板"],
      );

      if (healed.length) {
        append(
          "assistant",
          `已自动复位代码可修任务（${healed.length}）：${healed.join(", ")}。可再点「运行资产生成」。`,
          undefined,
          undefined,
          ["运行资产生成", "打开看板"],
        );
      }
      if (!advice.suitable || !needs.length) {
        if (!healed.length && !needs.length) {
          append("assistant", "当前没有需要项目经理处理的 failed 任务。");
        } else if (!advice.suitable) {
          append("assistant", "按诊断结果：不必调用项目经理 Agent，直接重跑即可。");
        }
        return;
      }
      const payload = needs
        .map(
          (n, i) =>
            `${i + 1}. task=${n.task_id} kind=${n.kind} pm_fit=${n.pm_fit}\n   ${String(n.pm_tip || n.summary || "").slice(0, 200)}`,
        )
        .join("\n");
      const pm = chatStore.roster.find((c) => c.roleKind === "product_host");
      if (!pm) {
        append(
          "assistant",
          `适合项目经理处理，但还没有项目经理同事。请先「+ 雇佣」一位。\n\n${payload}`,
          undefined,
          undefined,
          ["打开看板"],
        );
        return;
      }
      append(
        "assistant",
        `结论：**适合**交给 **${pm.displayName}**（${needs.length} 项）。正在调用…`,
        undefined,
        undefined,
        ["打开看板"],
      );
      const msg =
        `流水线失败需要你分诊（已判定适合项目经理处理）：\n${payload}\n\n` +
        `config_size / config_proxy → 用白名单命令改配置，再 pipeline reset --cascade；不要改内核代码。\n` +
        `validation → reset 后 pipeline run --run-prompts。\n` +
        `在 cli_hints / gui_hints 给出可执行下一步。不要空话。`;
      clearBusy(busyId);
      await handleAgentTurn(msg, { instanceId: pm.id });
      return;
    } catch (e) {
      append("assistant", `处理失败：${e instanceof Error ? e.message : String(e)}`);
    } finally {
      clearBusy(busyId);
    }
  };

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
        "尚未选定 **北极星图**（全局或任一场景的 `visual_reference`）。建议先点 **② 北极星图** 生成并选用，风格才容易一致。\n\n仍要直接跑资产？再点一次「运行资产生成」。",
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
      const runData = (res.data || null) as PipelineRunPayload | null;
      const statusAfter = await refreshManifest(selectedManifest);

      if (
        res.exitCode !== 0 ||
        Boolean(runData?.paused) ||
        Boolean(runData?.blocked) ||
        runData?.complete === false
      ) {
        let advice = formatPmFitAdvice(null);
        let healed: string[] = [];
        try {
          const diag = window.gameFactory.pipelineDiagnose
            ? await window.gameFactory.pipelineDiagnose(selectedManifest)
            : null;
          advice = formatPmFitAdvice(diag?.data);
          if (window.gameFactory.pipelineHeal) {
            const heal = await window.gameFactory.pipelineHeal(selectedManifest, true);
            healed = (heal.data?.healed as string[] | undefined) || [];
            if (healed.length) {
              await refreshManifest(selectedManifest);
            }
          }
        } catch {
          /* diagnose/heal best-effort */
        }
        // Re-read status after heal so progress/next-step match reality
        const statusNow =
          healed.length > 0 ? await refreshManifest(selectedManifest) : statusAfter;
        const plan = planPipelineStop({
          exitCode: res.exitCode,
          runData,
          advice,
          healed,
          status: statusNow?.status || status,
        });
        const rawTail = (res.stderr || "").trim()
          ? `\n\n日志摘录：\n${(res.stderr || "").slice(0, 400)}`
          : "";
        append(
          "assistant",
          `**${plan.title}**\n\n${plan.body}${rawTail}`,
          undefined,
          undefined,
          plan.choices,
        );
      } else {
        const counts = statusAfter?.status?.counts || status?.counts || {};
        const pending = Number(counts.pending ?? 0);
        const ready = statusAfter?.status?.ready_ids?.length ?? status?.ready_ids?.length ?? 0;
        if (pending > 0 || ready > 0) {
          append(
            "assistant",
            `**本轮跑完，流水线未全部完成**\n\n` +
              `进度：完成 ${counts.done ?? "?"} · 待跑 ${pending}` +
              (ready ? `（${ready} 个已就绪）` : "") +
              `\n\n**推荐下一步 → 运行资产生成**（续跑）`,
            undefined,
            undefined,
            ["运行资产生成", "打开看板"],
          );
        } else {
          append(
            "assistant",
            "**流水线已全部完成。** 可在看板或资产表查看，或继续派工给程序员。",
            undefined,
            undefined,
            ["打开看板", "打开资产表"],
          );
        }
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
        setSidePanel(null);
        openSettings("env");
        return;
      }
      append(
        "assistant",
        formatEnvHealthChat(health),
        undefined,
        undefined,
        health.ok ? ["打开环境"] : ["打开环境", "打开设置"],
      );
      setSidePanel(null);
      openSettings("env");
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

  const listBriefScenesForVt = (): VtSceneMark[] => {
    const byId = new Map(vtScenesFromStatus.map((s) => [s.id, s]));
    const raw = briefDraft?.project?.scenes;
    if (Array.isArray(raw) && raw.length) {
      const out: VtSceneMark[] = [];
      for (const row of raw) {
        if (!row || typeof row !== "object") continue;
        const rec = row as Record<string, unknown>;
        const id = String(rec.id || "").trim();
        const title = String(rec.title || "").trim() || id;
        if (!id) continue;
        const mark = byId.get(id);
        out.push({
          id,
          title,
          ready: mark?.ready,
          selected_id: mark?.selected_id ?? null,
          has_selected_image: mark?.has_selected_image,
          visual_reference: mark?.visual_reference,
          preview_path: mark?.preview_path,
        });
      }
      if (out.length) return out;
    }
    return vtScenesFromStatus;
  };

  /** When brief has scenes, ask global vs scene; otherwise generate immediately. */
  const promptVisualTargetScope = () => {
    const scenes = listBriefScenesForVt();
    if (!scenes.length) {
      void handleVisualTargetGenerate(null);
      return;
    }
    const choices = [
      formatVtGlobalChoiceLabel(vtGlobalMark),
      ...scenes.map((s) => formatVtSceneChoiceLabel(s)),
    ];
    append(
      "assistant",
      formatVtProgressBoard(vtGlobalMark, scenes) +
        "\n\n请选 **全局默认** 或某一个场景的北极星（反差大的屏建议各出一张）。",
      undefined,
      undefined,
      choices,
    );
  };

  const handleVisualTargetGenerate = async (sceneId: string | null = null) => {
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
        setSidePanel(null);
        openSettings("providers");
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
      setSidePanel(null);
      openSettings("providers");
      return;
    }
    const busyId = activeColleague.id;
    markBusy(busyId);
    setLogs([]);
    const sid = (sceneId || "").trim() || null;
    pendingVtSceneIdRef.current = sid;
    pendingVtGenerateRef.current = null;
    const focus = vtRestyleFocusRef.current;
    if (focus.active && focus.sceneId !== sid) {
      // Picking a different scope ends the restyle lock.
      vtRestyleFocusRef.current = { active: false, sceneId: null };
      setVtRestyleAwaitingText(false);
    }
    const sceneMeta = sid
      ? listBriefScenesForVt().find((s) => s.id === sid)
      : null;
    const sceneTitle = sceneMeta?.title || sid || "";
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
        sid
          ? `正在为场景 **${sceneTitle}**（\`${sid}\`）生成北极星候选…\n完成后点「选用北极星 a/b/c」。`
          : "正在生成北极星候选图（整屏玩法预览）…\n完成后点「选用北极星 a/b/c」。",
      );
      // Session draft art_direction does NOT auto-export — sync into disk brief first
      // so "大改风格" chats actually affect visual-target generate.
      if (briefDraft?.project && window.gameFactory.patchBriefProject) {
        const draftProj = briefDraft.project as Record<string, unknown>;
        const patch: Record<string, unknown> = {};
        for (const key of ["art_direction", "description", "player_asset", "camera", "hud"] as const) {
          if (draftProj[key] !== undefined && draftProj[key] !== null && draftProj[key] !== "") {
            patch[key] = draftProj[key];
          }
        }
        if (Object.keys(patch).length > 0) {
          const synced = await window.gameFactory.patchBriefProject(brief, patch);
          if (synced.ok && synced.changed && synced.changed.length > 0) {
            append(
              "assistant",
              `已把会话草稿写入 Brief 再生成：\`${synced.changed.join("`, `")}\`\n（以前只改对话、不导出时，北极星一直读旧磁盘 Brief，所以看起来「怎么改都差不多」。）`,
            );
            append("log", `brief patch: ${synced.changed.join(", ")}`);
          } else if (!synced.ok) {
            append(
              "assistant",
              `警告：未能把草稿写入 Brief（${synced.error || "unknown"}）。将继续用磁盘上的旧 Brief 生成。`,
            );
          }
        }
      } else if (!briefDraft?.project) {
        append(
          "log",
          "无会话草稿可同步 — 使用磁盘 Brief。若刚在策划里改了风格，请确认草稿里已有 art_direction，或先导出 Brief。",
        );
      }
      append(
        "log",
        sid ? `visual-target generate --scene ${sid} 开始…` : "visual-target generate 开始…",
      );
      const res = await window.gameFactory.visualTargetGenerate(brief, 3, sid);
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
      const manifestFromGenerate = String(data.manifest_path || "").trim();
      if (manifestFromGenerate) {
        pendingVtGenerateRef.current = {
          manifestPath: manifestFromGenerate,
          sceneId: sid,
        };
      }
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
          .map((id) =>
            sid
              ? formatVtPickChoice(id, sid, sceneTitle || sid)
              : formatVtPickChoice(id, null),
          ),
        formatVtRestyleChoice(sid, sceneTitle || undefined),
      ];
      append(
        "assistant",
        gallery.length
          ? sid
            ? `场景 **${sceneTitle}**（\`${sid}\`）的北极星候选已生成。满意就点带场景 id 的「选用北极星 …」。不满意就点「都不满意，重做（场景：…）」——先说哪里不对，**不会**自动改画风。`
            : "北极星候选已生成。点缩略图可看大图；满意就「选用北极星 …」。都不满意就点「都不满意，重做 · 全局」，先说哪里不对再重生成。"
          : "北极星流程已结束（可能无预览路径）。可「生成北极星图」重试，或「都不满意，重做」。",
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

  const shareChoicesAfterPick = (pickedSceneId: string | null): string[] => {
    const scenes = listBriefScenesForVt();
    if (!scenes.length) return [];
    const others = scenes.filter((s) => s.id !== pickedSceneId);
    if (!others.length) return [];
    return [
      ...others.map((s) => `也用于 · ${s.title}（${s.id}）`),
      "也用于 · 全部场景",
    ];
  };

  const handleVisualTargetPick = async (
    candidateId: string,
    sceneId?: string | string[] | null,
  ) => {
    const briefRel = activeBriefRel;
    if (!briefRel) {
      append("assistant", "还没有 Brief，无法选用北极星。");
      return;
    }
    if (!window.gameFactory?.visualTargetPick) {
      append("assistant", "当前客户端不支持选用北极星，请重启 Electron。");
      return;
    }
    // Prefer scene from the chip. Bare「选用北极星 a」= global (do not fall back
    // to pending scene — that made old chips write the wrong screen).
    let sids = Array.isArray(sceneId)
      ? sceneId.map((s) => String(s || "").trim()).filter(Boolean)
      : sceneId
        ? [String(sceneId).trim()]
        : [];
    const primarySid = sids[0] || null;
    const sceneMeta = primarySid
      ? listBriefScenesForVt().find((s) => s.id === primarySid)
      : null;
    const sceneTitle = sceneMeta?.title || primarySid || "";
    const busyId = activeColleague.id;
    markBusy(busyId);
    try {
      const pendingGen = pendingVtGenerateRef.current;
      const pickSid = primarySid || null;
      // Only pin --manifest when it belongs to the same scope as this pick
      // (avoids writing a newer combat generate into an older 「钓场」 chip).
      const manifestPath =
        pendingGen &&
        (pendingGen.sceneId || null) === pickSid &&
        pendingGen.manifestPath
          ? pendingGen.manifestPath
          : null;
      const res = await window.gameFactory.visualTargetPick(
        briefRel,
        candidateId,
        sids.length ? sids : null,
        manifestPath,
      );
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
      // scene_ids = intentional pick scope only; auto_matched is separate.
      const applied = res.data?.scene_ids?.length
        ? res.data.scene_ids
        : primarySid
          ? [primarySid]
          : [];
      const autoMatched = res.data?.auto_matched_scene_ids || [];
      const alreadyCovered = new Set([...applied, ...autoMatched]);
      const matchMethod = res.data?.auto_match_method || "";
      const pickedScene = primarySid || applied[0] || null;
      lastVtPickSourceRef.current = pickedScene
        ? { kind: "scene", sceneId: pickedScene }
        : { kind: "global" };
      const pickTitle =
        listBriefScenesForVt().find((s) => s.id === pickedScene)?.title ||
        sceneTitle ||
        pickedScene ||
        "";
      // End restyle/pick lock after a successful pick — do not wrap all later
      // planner turns as "刚选定该场景" (that polluted unrelated chat).
      vtRestyleFocusRef.current = { active: false, sceneId: null };
      setVtRestyleAwaitingText(false);
      await refreshVisualTarget(briefRel);
      // Re-hydrate host-chat from disk so策划 draft sees the new scene refs
      // (pick writes brief.json + mirrors brief.draft.json; bind skips stale flush).
      void syncPlannerProject(briefRel);
      const share = shareChoicesAfterPick(pickedScene).filter((c) => {
        if (c === "也用于 · 全部场景") {
          return listBriefScenesForVt().some((s) => !alreadyCovered.has(s.id));
        }
        const m = c.match(/（([a-zA-Z0-9_-]+)）$/);
        return m ? !alreadyCovered.has(m[1]) : true;
      });
      const labelFor = (id: string) => {
        const t = listBriefScenesForVt().find((s) => s.id === id)?.title || id;
        return `${t}（${id}）`;
      };
      const appliedLabel = applied.length ? applied.map(labelFor).join("、") : "";
      const autoLabel = autoMatched.length ? autoMatched.map(labelFor).join("、") : "";
      const scopeLine = pickedScene
        ? `**已选定场景：${pickTitle || pickedScene}**（\`${pickedScene}\`）· 候选 \`${candidateId}\``
        : `**已选定全局北极星** · 候选 \`${candidateId}\``;
      append(
        "assistant",
        `${scopeLine}\n\n` +
          (applied.length
            ? `\`scenes[${pickedScene || applied.join(",")}].visual_reference\` → \`${ref}\`\n\n`
            : `\`project.visual_reference\` → \`${ref}\`\n\n`) +
          (appliedLabel && applied.length > 1 ? `一并写入：${appliedLabel}\n\n` : "") +
          (autoLabel
            ? `另自动匹配到空场景：${autoLabel}` +
              (matchMethod ? `（${matchMethod}）` : "") +
              "（不是你刚点的主场景；不对就用「也用于」改）。\n\n"
            : share.length
              ? "其他空场景未自动命中。需要共用可点「也用于 …」。\n\n"
              : "") +
          "后续若要改这张图，直接说具体哪里不对；再点「都不满意，重做…」才会钉住场景反馈。可点 **去找项目经理**，或继续为其他场景生成北极星。",
        undefined,
        undefined,
        [
          ...share,
          "切换到项目经理",
          "切换到项目经理并生成流水线",
          "生成北极星图",
        ],
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

  const handleVisualTargetAssign = async (targetSceneIds: string[]) => {
    const briefRel = activeBriefRel;
    if (!briefRel) {
      append("assistant", "还没有 Brief，无法分配北极星。");
      return;
    }
    if (!window.gameFactory?.visualTargetAssign) {
      append("assistant", "当前客户端不支持共享北极星，请重启 Electron。");
      return;
    }
    const targets = targetSceneIds.map((s) => s.trim()).filter(Boolean);
    if (!targets.length) return;
    const source = lastVtPickSourceRef.current;
    const opts =
      source?.kind === "scene" && source.sceneId
        ? { fromScene: source.sceneId }
        : { fromGlobal: true as const };
    const busyId = activeColleague.id;
    markBusy(busyId);
    try {
      const res = await window.gameFactory.visualTargetAssign(briefRel, targets, opts);
      if (res.exitCode !== 0) {
        append(
          "assistant",
          `共享失败：${(res.stderr || res.stdout || "").slice(0, 800)}`,
          undefined,
          undefined,
          ["生成北极星图"],
        );
        return;
      }
      const ref = res.data?.visual_reference || "";
      const applied = Array.isArray(res.data?.scene_ids) ? res.data.scene_ids : [];
      const skipped = Array.isArray(res.data?.skipped_scene_ids)
        ? res.data.skipped_scene_ids
        : [];
      await refreshVisualTarget(briefRel);
      void syncPlannerProject(briefRel);
      const stillShare = shareChoicesAfterPick(
        source?.kind === "scene" ? source.sceneId || null : null,
      ).filter((c) => {
        if (c === "也用于 · 全部场景") {
          return listBriefScenesForVt().some(
            (s) => !applied.includes(s.id) && !skipped.includes(s.id),
          );
        }
        const m = c.match(/（([a-zA-Z0-9_-]+)）$/);
        return m ? !applied.includes(m[1]) : true;
      });
      if (!applied.length) {
        append(
          "assistant",
          (skipped.length
            ? `没有写入新场景：这些场景已有不同的北极星，已跳过：${skipped.join(", ")}。\n\n` +
              "若要强制覆盖，请用 CLI：`brief visual-target assign --force …`。\n\n"
            : "没有写入任何场景。\n\n") +
            "可给空场景单独生成，或先清掉该场景的 `visual_reference` 再点「也用于」。",
          undefined,
          undefined,
          ["生成北极星图", "切换到项目经理"],
        );
        return;
      }
      append(
        "assistant",
        `✓ 已把同一北极星挂到场景：${applied.join(", ")}\n\n` +
          `共用路径 → \`${ref}\`\n\n` +
          (skipped.length
            ? `已跳过（已有不同图）：${skipped.join(", ")}\n\n`
            : "") +
          "这些场景的资产会解析到同一张图（不必再出一遍候选）。",
        undefined,
        undefined,
        [
          ...stillShare,
          "切换到项目经理",
          "切换到项目经理并生成流水线",
          "生成北极星图",
        ],
      );
    } catch (e) {
      append(
        "assistant",
        `共享北极星异常：${e instanceof Error ? e.message : String(e)}`,
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

      const preferred = (await resolvePlanTargets(briefRel)).manifestRel;
      const manifests = await window.gameFactory.listManifests();
      const existing =
        window.gameFactory.findManifestForBrief &&
        (await window.gameFactory.findManifestForBrief(briefRel));
      let reusePath = "";
      if (manifests.some((m) => m.path === preferred)) {
        reusePath = preferred;
      } else if (existing?.path && manifests.some((m) => m.path === existing.path)) {
        const metaBrief = String(existing.meta?.brief || "").replace(/\\/g, "/");
        if (!metaBrief || sameProjectRoot(metaBrief, briefRel)) {
          reusePath = existing.path;
        }
      }
      if (reusePath) {
        setSelectedManifest(reusePath);
        await refreshManifest(reusePath);
        const meta =
          (existing?.path === reusePath ? existing.meta : null) ||
          (await window.gameFactory.getManifestMeta(reusePath));
        append(
          "assistant",
          summarizeManifest(reusePath, meta) + "\n\n（已按 Brief 匹配到现有清单，未重复生成。）",
          undefined,
          undefined,
          ["北极星图", "运行资产生成（含文案）", "打开看板"],
        );
        setSidePanel("board");
        return;
      }

      const targets = await resolvePlanTargets(briefRel);
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
    // Prefer active brief's game/ — never open another project's Godot from a stale manifest
    let projectRel = activeBriefRel
      ? (await resolvePlanTargets(activeBriefRel)).godotProjectRel
      : null;
    if (selectedManifest && activeBriefRel) {
      try {
        const meta = await window.gameFactory.getManifestMeta(selectedManifest);
        const metaBrief = String(meta?.brief || "").replace(/\\/g, "/");
        if (
          meta?.godot_project &&
          (!metaBrief || sameProjectRoot(metaBrief, activeBriefRel))
        ) {
          projectRel = meta.godot_project;
        }
      } catch {
        /* keep brief-derived path */
      }
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
      const planTargets = await resolvePlanTargets(activeBriefRel);
      const productionRel = planTargets.productionRel;
      const progressRel = planTargets.progressRel;
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
      openSettings("env");
      append("assistant", "已打开设置 → **环境**。可点「重新检测」；有红色项把原文发给支持。");
      return;
    }
    if (trimmed === "打开设置") {
      openSettings("providers");
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
    const restyle = parseVtRestyleChoice(trimmed);
    if (restyle.hit) {
      const sid =
        restyle.sceneId === undefined
          ? pendingVtSceneIdRef.current
          : restyle.sceneId;
      const sceneMeta = sid
        ? listBriefScenesForVt().find((s) => s.id === sid)
        : null;
      const sceneTitle = sceneMeta?.title || sid || "";
      pendingVtSceneIdRef.current = sid;
      vtRestyleFocusRef.current = {
        active: true,
        sceneId: sid,
        sceneTitle: sceneTitle || undefined,
        kind: "restyle",
        feedbackDone: false,
      };
      setVtRestyleAwaitingText(true);
      if (agentRole !== "brief") {
        append(
          "assistant",
          sid
            ? `候选不满意请切到 **策划**：当前钉住场景 **${sceneTitle}**（\`${sid}\`）。\n\n先在输入框说明哪里不对（构图/内容/钓点/UI 都行——**不一定是风格**）。说完再重生成；不要空改画风。`
            : "候选不满意请切到 **策划**：先在输入框说明哪里不对，再重生成。",
          undefined,
          undefined,
          ["生成北极星图（改选其他范围）"],
        );
        return;
      }
      append(
        "assistant",
        sid
          ? `好。已钉住场景 **${sceneTitle}**（\`${sid}\`）。\n\n「都不满意」**不等于换画风**。请先在下方输入框写**具体哪里不对**（例如「不是完整地图」「没有钓点标记」「按钮太大」）。\n\n写完发送后才会出现「重新生成」——在此之前不会改 brief、不会出图。`
          : "好。已钉住 **全局** 北极星重做。\n\n「都不满意」**不等于换画风**。请先写具体哪里不对，发送后再出现「重新生成」。",
        undefined,
        undefined,
        ["生成北极星图（改选其他范围）"],
      );
      setBrainstormActive(true);
      setBrainstormChoices(["生成北极星图（改选其他范围）"]);
      return;
    }
    {
      const regen = parseVtRegenAfterFeedbackChoice(trimmed);
      if (regen.hit) {
        if (agentRole !== "brief" && agentRole !== "product_host") {
          append("assistant", "重新生成北极星请切换到 **策划** 或 **项目经理**。");
          return;
        }
        const focus = vtRestyleFocusRef.current;
        if (focus.active && focus.kind === "restyle" && !focus.feedbackDone) {
          append(
            "assistant",
            "还没收到你的文字反馈。请先在输入框说明哪里不对，发送后再点「我写好了 · 重新生成」。",
          );
          return;
        }
        const sid = regen.sceneId; // null = explicit global; never fall back to focus
        await handleVisualTargetGenerate(sid);
        return;
      }
    }
    if (
      trimmed === "北极星图" ||
      trimmed === "生成北极星" ||
      trimmed === "生成北极星图"
    ) {
      if (agentRole !== "brief" && agentRole !== "product_host") {
        append("assistant", "生成北极星请切换到 **策划** 或 **项目经理**。");
        return;
      }
      const focus = vtRestyleFocusRef.current;
      if (focus.active && focus.kind === "restyle" && !focus.feedbackDone) {
        append(
          "assistant",
          focus.sceneId
            ? `正在重做 **${focus.sceneTitle || focus.sceneId}** 的北极星。请先在输入框写反馈并发送，出现「我写好了 · 重新生成」后再出图。`
            : "正在重做全局北极星。请先在输入框写反馈并发送，再点重新生成。",
        );
        return;
      }
      if (focus.active && focus.kind === "restyle" && focus.feedbackDone) {
        await handleVisualTargetGenerate(focus.sceneId);
        return;
      }
      promptVisualTargetScope();
      return;
    }
    if (trimmed === "生成北极星图（改选其他范围）") {
      if (agentRole !== "brief" && agentRole !== "product_host") {
        append("assistant", "生成北极星请切换到 **策划** 或 **项目经理**。");
        return;
      }
      vtRestyleFocusRef.current = { active: false, sceneId: null };
      setVtRestyleAwaitingText(false);
      promptVisualTargetScope();
      return;
    }
    if (
      trimmed === "生成北极星 · 全局" ||
      trimmed === "生成北极星图 · 全局" ||
      /^生成北极星(?:图)?\s*[·•]\s*(?:[○✓][a-dA-D]?\s+)?全局$/.test(trimmed)
    ) {
      if (agentRole !== "brief" && agentRole !== "product_host") {
        append("assistant", "生成北极星请切换到 **策划** 或 **项目经理**。");
        return;
      }
      await handleVisualTargetGenerate(null);
      return;
    }
    {
      // Scene id may be after nested title parens — take id after ｜ or last （ascii）.
      const genScene = trimmed.match(/^生成北极星(?:图)?\s*[·•]\s*(.+)$/);
      if (genScene) {
        if (agentRole !== "brief" && agentRole !== "product_host") {
          append("assistant", "生成北极星请切换到 **策划** 或 **项目经理**。");
          return;
        }
        const focus = vtRestyleFocusRef.current;
        if (focus.active && focus.kind === "restyle" && !focus.feedbackDone) {
          append(
            "assistant",
            "请先在输入框写反馈并发送；写完后会出现「我写好了 · 重新生成」，再出图。",
          );
          return;
        }
        const sid = extractSceneIdFromChoice(genScene[1]);
        if (!sid) {
          append("assistant", "没法识别场景 id，请再点带（scene_id）的按钮。");
          return;
        }
        await handleVisualTargetGenerate(sid);
        return;
      }
    }
    {
      const pick = parseVtPickChoice(trimmed);
      if (pick.hit) {
        await handleVisualTargetPick(pick.candidateId, pick.sceneId);
        return;
      }
    }
    if (trimmed === "也用于 · 全部场景") {
      const source = lastVtPickSourceRef.current;
      const all = listBriefScenesForVt()
        .map((s) => s.id)
        .filter((id) => !(source?.kind === "scene" && source.sceneId === id));
      await handleVisualTargetAssign(all.length ? all : listBriefScenesForVt().map((s) => s.id));
      return;
    }
    {
      const shareMatch = trimmed.match(/^也用于\s*[·•]\s*(.+)$/);
      if (shareMatch) {
        const sid = extractSceneIdFromChoice(shareMatch[1]);
        if (sid) {
          await handleVisualTargetAssign([sid]);
          return;
        }
      }
    }
    if (trimmed === "运行资产生成（含文案）") {
      if (agentRole !== "product_host" && agentRole !== "brief") {
        append("assistant", "运行资产生成请切换到 **项目经理**（或策划）。");
        return;
      }
      await handleRun(true);
      return;
    }
    if (trimmed === "运行资产生成" || trimmed === "运行 Pipeline") {
      if (agentRole !== "product_host" && agentRole !== "brief") {
        append("assistant", "运行资产生成请切换到 **项目经理**（或策划）。");
        return;
      }
      await handleRun(false);
      return;
    }
    if (trimmed === "项目经理处理失败") {
      await handlePipelinePmHeal();
      return;
    }
    if (trimmed === "打开看板") {
      toggleSidePanel("board");
      append("assistant", "已打开右侧任务看板。");
      return;
    }
    if (trimmed === "打开资产表" || trimmed === "打开资产") {
      toggleSidePanel("assets");
      append("assistant", "已打开右侧资产审查表。");
      return;
    }
    if (trimmed === "打开文档") {
      setSidePanel("docs");
      if (agentRole === "brief") void refreshBrainstormStatus();
      append(
        "assistant",
        activeBriefRel
          ? `已打开文档面板（工程 **${activeProjectLabel || slugFromBriefRel(activeBriefRel)}**）。`
          : "已打开文档面板。请先选择或导出工程。",
      );
      return;
    }
    if (pendingSafeActions.current.has(trimmed)) {
      if (agentRole === "advisor") {
        append("assistant", "顾问只咨询、不执行命令。请切换到 **项目经理** 或 **IT**。");
        return;
      }
      await handleSafeAction(trimmed);
      return;
    }

    // Fresh project: new GUI thread + wipe host-chat draft BEFORE appending the user turn.
    if (agentRole === "brief") {
      const briefCmdEarly = parseBriefSubcommand(text);
      const newProjectEarly = parseNewProjectIntent(text);
      if (briefCmdEarly?.action === "reset" || newProjectEarly) {
        const seed =
          briefCmdEarly?.action === "reset"
            ? briefCmdEarly.name
            : newProjectEarly?.seed;
        const slugHint =
          briefCmdEarly?.action === "reset"
            ? sanitizeProjectSlug(briefCmdEarly.name || "") || undefined
            : newProjectEarly?.slugHint;
        await runBriefReset(seed, {
          announcePath: true,
          userText: text,
          slugHint,
        });
        return;
      }
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
        // Should have been handled before append; keep as safety net.
        await runBriefReset(cmd.name, { announcePath: true });
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
    if (cmd === "/assets") {
      toggleSidePanel("assets");
      append("assistant", "资产表已切换 — 右侧审查缩略图与映射。");
      return;
    }
    if (cmd === "/settings") {
      openSettings("providers");
      append("assistant", "设置页已打开 — 编辑 API Key 与 Godot 路径。");
      return;
    }
    if (cmd === "/env") {
      openSettings("env");
      append("assistant", "设置 → **环境** — 可检测并安装本机工具。");
      return;
    }
    if (cmd === "/guide") {
      openSettings("guide");
      append("assistant", "设置 → **指南** — 查看对话指令与 CLI 速查。");
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
        `未知指令。可用：/brief /doctor /plan /run /board /assets /settings /env /guide /godot /delta`,
      );
      return;
    }

    const sendRoute = routeColleagueSend(agentRole, brainstormActive);
    if (sendRoute === "agent") {
      await handleAgentTurn(text, { instanceId: activeColleague.id });
      return;
    }
    if (sendRoute === "brief_turn") {
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
          <ProjectSwitcher
            variant="chip"
            activeBriefRel={activeBriefRel}
            activeProjectLabel={activeProjectLabel}
            onSelect={(rel) => void switchProject(rel)}
            onNewProject={() => {
              if (agentRole !== "brief") {
                append("assistant", "请先切换到 **策划** 同事，再点「新建项目」。");
                return;
              }
              openNewProjectModal({
                userText: "新建项目",
                announcePath: true,
                defaultSlug: "fishing-2d",
              });
            }}
          />
        </div>
        <div className="topbar__actions">
          {status && (
            <span className={`badge ${status.done ? "badge--ok" : "badge--idle"}`}>
              {status.done ? "已完成" : "进行中"}
            </span>
          )}
          <button
            type="button"
            className={`btn btn--ghost ${appView === "settings" ? "btn--active" : ""}`}
            onClick={() => {
              if (appView === "settings") closeSettings();
              else openSettings();
            }}
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
              // Opening docs with a stale unbind: soft-restore so project file chips appear
              if (!activeBriefRel) {
                const restored = loadActiveBriefRelForStartup();
                if (restored) {
                  setBrief(restored);
                  setDocsDiskRefreshKey((n) => n + 1);
                }
              } else {
                setDocsDiskRefreshKey((n) => n + 1);
              }
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
          <button
            type="button"
            className={`btn btn--ghost ${sidePanel === "assets" ? "btn--active" : ""}`}
            onClick={() => toggleSidePanel("assets")}
          >
            <svg viewBox="0 0 24 24" fill="none" width="16" height="16">
              <path
                d="M4 7.5L12 3l8 4.5v9L12 21l-8-4.5v-9z"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinejoin="round"
              />
              <path d="M12 12v9M4 7.5l8 4.5 8-4.5" stroke="currentColor" strokeWidth="1.5" />
            </svg>
            资产
          </button>
        </div>
      </header>
      <UpdateBanner />

      {appView === "settings" ? (
        <SettingsPage
          initialTab={settingsTab}
          onClose={closeSettings}
          busy={anyBusy}
          toolchain={toolchainReport}
          executorSetup={executorSetup}
          doctor={doctorReport}
          scanning={envScanning}
          installing={toolchainInstalling}
          executorBusy={executorBusy}
          installLog={toolchainLog}
          onRefreshEnv={() => void refreshEnv()}
          onInstall={(id) => void handleToolchainInstall(id)}
          onInstallAll={() => void handleToolchainInstallAll()}
          onExecutorStep={(id, step) => void handleExecutorStep(id, step)}
          onOpenExternal={(url) => void window.gameFactory.openExternal(url)}
        />
      ) : (
        <>
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
        onOpenEnv={() => openSettings("env")}
        onOpenGuide={() => openSettings("guide")}
      />

      <div
        className={`chat-layout ${sidePanel ? "side-open" : ""}`}
        onMouseMove={(e) => {
          if (!isResizingPanel.current) return;
          const dx = resizeStartX.current - e.clientX;
          const next = Math.max(240, Math.min(900, resizeStartW.current + dx));
          setSidePanelWidth(next);
        }}
        onMouseUp={() => {
          if (!isResizingPanel.current) return;
          isResizingPanel.current = false;
          document.body.style.cursor = "";
          document.body.style.userSelect = "";
        }}
        onMouseLeave={() => {
          if (!isResizingPanel.current) return;
          isResizingPanel.current = false;
          document.body.style.cursor = "";
          document.body.style.userSelect = "";
        }}
      >
        <ColleagueRoster
          roster={chatStore.roster}
          activeInstanceId={activeColleague.id}
          sessions={instanceSessions}
          activeSessionId={activeSession.id}
          openHandoffs={handoffsForRoster}
          busyInstanceIds={busyInstanceIds}
          onSelectColleague={handleSelectColleague}
          onRequestHire={handleRequestHire}
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
            scrollKey={activeSession.id}
            hideDialogChoices={messages.some(
              (m) => m.makeabilityCard?.status === "pending",
            )}
            onSuggestion={handleSend}
            onToolPermissionDecision={handleToolPermissionDecision}
            onMakeabilityAnswer={(messageId, answers) =>
              void handleMakeabilityAnswer(messageId, answers)
            }
            onMakeabilityRetry={(messageId) => {
              const msg = messages.find((m) => m.id === messageId);
              const last = msg?.makeabilityCard?.lastAnswers;
              if (last?.length) void handleMakeabilityAnswer(messageId, last);
            }}
            heroTitle={hero.title}
            heroSubtitle={hero.subtitle}
            suggestions={suggestions}
          />
          {agentRole === "brief" && activeBriefRel && (
            <div className="pm-sticky-actions" role="toolbar" aria-label="视觉定稿">
              <span className="pm-sticky-actions__label">视觉定稿</span>
              <span className="pm-sticky-actions__hint">
                {formatVtStickyHint(vtGlobalMark, listBriefScenesForVt())}
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
                title="生成整屏玩法预览候选；点开后可见各场景 ✓a/✓b/✓c 与绑定状态"
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
              <button
                type="button"
                className="pm-sticky-actions__btn"
                disabled={chatBusy}
                onClick={() => void handleSend("打开资产表")}
                title="右侧审查资产缩略图与映射"
              >
                资产
              </button>
            </div>
          )}
          <ColleagueConfigBar
            colleague={activeColleague}
            sessionId={activeSession.id}
            disabled={chatBusy}
            onPiSessionTrustChange={(trusted) => {
              itSessionTrustRef.current[activeColleague.id] = trusted;
            }}
            onSavingChange={(saving) => {
              agentConfigSavingRef.current = saving;
              setAgentConfigSaving(saving);
            }}
          />
          <ChatInput
            busy={chatBusy || agentConfigSaving}
            onStop={() => void handleStopChat()}
            hideDialogChoices={messages.some(
              (m) => m.makeabilityCard?.status === "pending",
            )}
            choices={
              agentRole === "brief"
                ? brainstormChoices.filter(
                    (c) =>
                      ![
                        "生成北极星图",
                        "生成北极星",
                        "北极星图",
                        "都不满意，换风格",
                        "都不满意，重做",
                        "生成北极星 · 全局",
                        "生成北极星图 · 全局",
                        "生成北极星图（改选其他范围）",
                        "保存 Brief",
                        "制作审查",
                        "补全细节",
                        "议题头脑风暴",
                        "自动修 brief",
                        "生成 UI 示意",
                      ].includes(c) &&
                      !/^生成北极星(?:图)?\s*[·•]/.test(c) &&
                      !/^都不满意，(?:重做|换风格)/.test(c) &&
                      !/^选用北极星\s*[a-dA-D]/.test(c) &&
                      !/^也用于\s*[·•]/.test(c),
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
                          "打开资产表",
                          "打开资产",
                        ].includes(c),
                    )
                  : agentActionChoices
            }
            readyToExport={briefExportReady}
            showAutofix={agentRole === "brief" && Boolean(briefDraft)}
            showMakeability={agentRole === "brief" && Boolean(briefDraft)}
            showEnrich={agentRole === "brief"}
            showUiWireframe={agentRole === "brief"}
            showTopicBrainstorm={agentRole === "brief"}
            exportGateHint={briefExportGateHint}
            placeholder={
              agentRole === "brief"
                ? vtRestyleAwaitingText
                  ? "先写这张北极星哪里不对，发送后再点「重新生成」…"
                  : "描述游戏想法，和策划商量设定…"
                : agentRole === "product_host"
                  ? "描述试玩问题或要推进的事…"
                  : "描述要改的代码或任务…"
            }
            onSend={handleSend}
            onChoice={(text) => {
              const adopt = text.match(/^采用\s+(p\d+)\s*[:：]/);
              if (adopt) {
                void handleBrainstormApply([adopt[1]], false);
                return;
              }
              if (text === "融合前两个方案") {
                void handleBrainstormApply(["p1", "p2"], true);
                return;
              }
              void handleSend(text);
            }}
            onWorkstation={
              agentRole === "brief"
                ? (action) => {
                    if (action === "makeability") void handleBriefMakeability();
                    else if (action === "enrich") void handleBriefEnrich();
                    else if (action === "topic") void handleTopicBrainstorm();
                    else if (action === "ui") void handleBriefUiWireframe();
                    else if (action === "autofix") void handleBriefAutofix(5);
                    else if (action === "export") void handleBriefExport();
                  }
                : undefined
            }
          />
        </section>

        {sidePanel !== null && (
          /* Drag handle between chat-column and the side panel */
          <div
            className="side-panel-resize-handle"
            onMouseDown={(e) => {
              e.preventDefault();
              isResizingPanel.current = true;
              resizeStartX.current = e.clientX;
              // measure current panel width from the next sibling
              const panel = (e.currentTarget as HTMLElement).nextElementSibling as HTMLElement | null;
              resizeStartW.current = panel ? panel.getBoundingClientRect().width : (sidePanelWidth ?? 380);
              document.body.style.cursor = "col-resize";
              document.body.style.userSelect = "none";
            }}
          />
        )}

        {sidePanel === "board" && (
          <BoardPanel
            style={sidePanelWidth ? { width: sidePanelWidth, minWidth: sidePanelWidth, maxWidth: sidePanelWidth } : undefined}
            manifest={selectedManifest}
            status={status}
            tasks={tasks}
            logs={logs}
            busy={anyBusy}
            draftBrief={briefDraft}
            vtGlobal={vtGlobalMark}
            vtScenes={listBriefScenesForVt()}
            onRefreshVt={() => {
              void refreshVisualTarget(activeBriefRel);
            }}
            onRefresh={() => refreshManifest(selectedManifest)}
            onRun={handleRun}
          />
        )}

        {sidePanel === "assets" && (
          <AssetReviewPanel
            style={sidePanelWidth ? { width: sidePanelWidth, minWidth: sidePanelWidth, maxWidth: sidePanelWidth } : undefined}
            assetsManifestRel={assetsManifestRel}
            pipelineManifestRel={selectedManifest || null}
            busy={anyBusy}
            onOpenBoard={() => setSidePanel("board")}
            onAfterRegenerate={() => {
              if (selectedManifest) void refreshManifest(selectedManifest);
            }}
          />
        )}

        {sidePanel === "docs" && (
          <DocsPreviewPanel
            key={activeBriefRel || "docs-unbound"}
            style={sidePanelWidth ? { width: sidePanelWidth, minWidth: sidePanelWidth, maxWidth: sidePanelWidth } : undefined}
            draftBrief={briefDraft}
            draftDocument={draftDocument}
            status={briefDraftStatus}
            activeBriefRel={activeBriefRel}
            externalEntryById={externalEntryById}
            activeProjectLabel={activeProjectLabel}
            readyToExport={briefExportReady}
            busy={chatBusy}
            diskRefreshKey={docsDiskRefreshKey}
            focusDiskRel={docsFocusDiskRel}
            onFocusDiskRelConsumed={() => setDocsFocusDiskRel(null)}
            onSelectProject={(rel) => void switchProject(rel)}
            onNewProject={() => {
              if (agentRole !== "brief") {
                append("assistant", "请先切换到 **策划** 同事，再点「新建项目」。");
                return;
              }
              openNewProjectModal({
                userText: "新建项目",
                announcePath: true,
                defaultSlug: "fishing-2d",
              });
            }}
            onRefresh={() => {
              if (agentRole === "brief") void refreshBrainstormStatus();
            }}
            onAutofix={agentRole === "brief" ? () => void handleBriefAutofix(5) : undefined}
            onMakeability={agentRole === "brief" ? () => void handleBriefMakeability() : undefined}
            onEnrich={agentRole === "brief" ? () => void handleBriefEnrich() : undefined}
            onUiWireframe={agentRole === "brief" ? () => void handleBriefUiWireframe() : undefined}
            onTopicBrainstorm={agentRole === "brief" ? () => void handleTopicBrainstorm() : undefined}
            onRefreshZhDoc={agentRole === "brief" ? () => void handleBriefZhDoc() : undefined}
            onExportBrief={agentRole === "brief" ? () => void handleBriefExport() : undefined}
          />
        )}

      </div>
        </>
      )}

      <NewProjectModal
        open={newProjectOpen}
        defaultSlug={newProjectDefaultSlug}
        onCancel={() => {
          setNewProjectOpen(false);
          pendingNewProjectRef.current = null;
        }}
        onBind={(slug) => {
          setNewProjectOpen(false);
          pendingNewProjectRef.current = null;
          void (async () => {
            const created = await ensureAndBindProject(slug);
            if (!created) return;
            await syncPipelineForBrief(created.briefRel);
            const bound = await syncPlannerProject(created.briefRel);
            setSidePanel("docs");
            const assetN = bound?.asset_count ?? 0;
            const title = bound?.title || created.slug;
            append(
              "assistant",
              [
                `**已绑定工程** \`${created.slug}\``,
                "",
                `- 目录：\`projects/${created.slug}/\``,
                `- 策划已识别本工程${title ? `（${title}）` : ""}`,
                assetN > 0
                  ? `- 已从磁盘载入工作草稿（${assetN} 个资产）`
                  : "- 尚无磁盘草稿，可在对话里继续扩写",
                "- 右侧文档只显示本工程；看板已按本工程同步",
                "",
                "若要清空对话重开，再点「新建项目」→「绑定并新开对话」。",
              ].join("\n"),
              undefined,
              undefined,
              ["打开文档", "继续完善 brief"],
            );
          })();
        }}
        onBindAndReset={(slug) => {
          setNewProjectOpen(false);
          const pending = pendingNewProjectRef.current;
          pendingNewProjectRef.current = null;
          void runBriefReset(pending?.seed, {
            announcePath: pending?.announcePath !== false,
            userText: pending?.userText || "新建项目",
            slugHint: slug,
          });
        }}
      />

      {hireRoleKind && (
        <HireColleagueModal
          roleKind={hireRoleKind}
          roster={chatStore.roster}
          onCancel={handleHireCancel}
          onConfirm={handleHireConfirm}
        />
      )}

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
            openSettings("providers");
          }}
        />
      )}
    </div>
  );
}
