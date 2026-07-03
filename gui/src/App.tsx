import { useCallback, useEffect, useState } from "react";
import type { PipelineStatus, PipelineTask } from "./vite-env.d";
import { ChatView } from "./components/ChatView";
import { ChatInput } from "./components/ChatInput";
import { BoardPanel } from "./components/BoardPanel";
import { SettingsPanel } from "./components/SettingsPanel";
import { ToolchainModal } from "./components/ToolchainModal";
import type { ToolchainReport } from "./settings/toolchain";
import { autoInstallable } from "./settings/toolchain";
import { newMessageId, parseChatCommand, parseRunFlags, type ChatAttachment, type ChatMessage } from "./chat/types";
import { extractMediaPaths, mergeAttachments } from "./chat/extractMediaPaths";
import {
  loadActiveBriefRel,
  parsePlanSubcommand,
  planTargetsFromBrief,
  saveActiveBriefRel,
} from "./chat/projectPaths";

type SidePanel = "board" | "settings" | null;

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
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sidePanel, setSidePanel] = useState<SidePanel>(null);
  const [busy, setBusy] = useState(false);
  const [brainstormActive, setBrainstormActive] = useState(false);
  const [brainstormChoices, setBrainstormChoices] = useState<string[]>([]);
  const [brainstormReady, setBrainstormReady] = useState(false);
  const [draftTitle, setDraftTitle] = useState("");
  const [toolchainReport, setToolchainReport] = useState<ToolchainReport | null>(null);
  const [toolchainDismissed, setToolchainDismissed] = useState(false);
  const [toolchainInstalling, setToolchainInstalling] = useState<string | null>(null);
  const [toolchainLog, setToolchainLog] = useState<string[]>([]);

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
    (content: string, choices?: string[], attachments?: ChatAttachment[]) => {
      setMessages((prev) => [
        ...prev,
        {
          id: newMessageId(),
          role: "assistant",
          content,
          timestamp: Date.now(),
          choices: choices?.length ? choices : undefined,
          attachments: attachments?.length ? attachments : undefined,
        },
      ]);
      setBrainstormChoices(choices || []);
    },
    [],
  );

  const applyBrainstormResult = useCallback(
    (data: {
      assistant_message?: string;
      choices?: string[];
      ready_to_export?: boolean;
      draft_brief?: { project?: { title?: string } };
    }) => {
      if (!data.assistant_message) return;
      setBrainstormActive(true);
      appendAssistant(data.assistant_message, data.choices);
      setBrainstormReady(Boolean(data.ready_to_export));
      const title = data.draft_brief?.project?.title;
      if (title) setDraftTitle(String(title));
    },
    [appendAssistant],
  );

  const refreshBrainstormStatus = useCallback(async () => {
    if (!window.gameFactory?.briefBrainstormStatus) return;
    const res = await window.gameFactory.briefBrainstormStatus();
    const data = res.data;
    if (data?.exists && (data.message_count || 0) > 0) {
      setBrainstormActive(true);
      setBrainstormReady(Boolean(data.ready_to_export));
      setBrainstormChoices(data.last_choices || []);
      if (data.title) setDraftTitle(data.title);
    }
  }, []);

  const append = useCallback(
    (role: ChatMessage["role"], content: string, attachments?: ChatAttachment[]) => {
      setMessages((prev) => [
        ...prev,
        {
          id: newMessageId(),
          role,
          content,
          timestamp: Date.now(),
          attachments: attachments?.length ? attachments : undefined,
        },
      ]);
    },
    [],
  );

  const handleBrainstormStart = async (seed?: string) => {
    setBusy(true);
    setBrainstormChoices([]);
    try {
      const res = await window.gameFactory.briefBrainstormStart(seed);
      if (res.exitCode !== 0 || !res.data?.assistant_message) {
        throw new Error(res.stderr || res.stdout || "brainstorm start failed");
      }
      applyBrainstormResult(res.data);
    } catch (e) {
      appendAssistant(
        `Brief 策划启动失败：${e instanceof Error ? e.message : String(e)}\n\n请先在 **设置 → 在线服务 → 项目经理** 配置 API Key。`,
      );
    } finally {
      setBusy(false);
    }
  };

  const handleBrainstormTurn = async (message: string) => {
    setBusy(true);
    setBrainstormChoices([]);
    try {
      let res = await window.gameFactory.briefBrainstormTurn(message);
      if (res.exitCode !== 0 && /Session not found/i.test(res.stderr || res.stdout || "")) {
        res = await window.gameFactory.briefBrainstormStart(message);
      }
      if (res.exitCode !== 0 || !res.data?.assistant_message) {
        throw new Error(res.stderr || res.stdout || "brainstorm turn failed");
      }
      applyBrainstormResult(res.data);
    } catch (e) {
      appendAssistant(`回复失败：${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setBusy(false);
    }
  };

  const handleBriefExport = async (nameHint?: string) => {
    setBusy(true);
    try {
      const slug = slugifyBriefName(nameHint || draftTitle || "my-game");
      const outputRel = `resources/${slug}-brief.json`;
      const res = await window.gameFactory.briefBrainstormExport(outputRel);
      if (res.exitCode !== 0) {
        throw new Error(res.stderr || res.stdout || "export failed");
      }
      const path = res.data?.brief_path || outputRel;
      setBrief(outputRel);
      appendAssistant(
        `**Brief 已保存**\n\n\`${path}\`\n\n发送 \`/plan\` 生成流水线 manifest，再 \`/run\` 执行。`,
      );
    } catch (e) {
      appendAssistant(`导出失败：${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setBusy(false);
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

  const loadInitial = useCallback(async () => {
    if (!window.gameFactory) return;
    await Promise.all([window.gameFactory.getPaths(), window.gameFactory.doctor()]);
    await refreshToolchain();

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
  }, [refreshManifest, activeBriefRel, setBrief, refreshToolchain]);

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
        await refreshToolchain();
        await window.gameFactory.doctor();
      } catch (e) {
        appendAssistant(`安装失败：${e instanceof Error ? e.message : String(e)}`);
      } finally {
        setToolchainInstalling(null);
      }
    },
    [appendAssistant, refreshToolchain],
  );

  const handleToolchainInstallAll = useCallback(async () => {
    if (!toolchainReport) return;
    for (const item of autoInstallable(toolchainReport)) {
      await handleToolchainInstall(item.id);
    }
  }, [toolchainReport, handleToolchainInstall]);

  useEffect(() => {
    void loadInitial()
      .then(() => refreshBrainstormStatus())
      .catch((e) =>
        append("system", `初始化失败：${e instanceof Error ? e.message : String(e)}`),
      );
    const off = window.gameFactory?.onPipelineLog(({ line }) => {
      setLogs((prev) => [...prev.slice(-200), line]);
      const found = extractMediaPaths(line);
      setMessages((prev) => {
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
      });
    });
    return off;
  }, [loadInitial, append, refreshBrainstormStatus]);

  const handleRun = async (runPrompts = false) => {
    if (!selectedManifest) {
      append("assistant", "还没有 pipeline manifest。请先完成 Brief 策划并发送 `/plan`。");
      return;
    }
    setBusy(true);
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
      setBusy(false);
    }
  };

  const handleDoctor = async () => {
    setBusy(true);
    try {
      const res = await window.gameFactory.doctor();
      const d = res.data;
      if (!d) {
        append("assistant", "doctor 无 JSON 输出。");
        return;
      }
      const caps = Object.entries(d.capabilities || {})
        .map(([k, ok]) => `${ok ? "✓" : "✗"} ${k}`)
        .join("\n");
      append(
        "assistant",
        `**环境探测**\n\n${caps}\n\nOpenRouter: ${d.config.openrouter_key}\nSeedance: ${d.config.seedance_key}\n\n（Hermes/Codex/Cursor 不随仓库分发，由本机探测）`,
      );
    } finally {
      setBusy(false);
    }
  };

  const handlePlan = async (explicitBrief?: string | null) => {
    setBusy(true);
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
      setBusy(false);
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

  const handleSend = async (text: string) => {
    append("user", text);

    const briefCmd = parseBriefSubcommand(text);
    if (briefCmd || text.trim().toLowerCase() === "/brief") {
      const cmd = briefCmd || { action: "start" as const };
      if (cmd.action === "reset") {
        setBrainstormActive(false);
        setBrainstormReady(false);
        setBusy(true);
        setBrainstormChoices([]);
        try {
          const res = await window.gameFactory.briefBrainstormReset(cmd.name);
          if (res.exitCode !== 0 || !res.data?.assistant_message) {
            throw new Error(res.stderr || res.stdout || "brainstorm reset failed");
          }
          applyBrainstormResult(res.data);
        } catch (e) {
          appendAssistant(`重置失败：${e instanceof Error ? e.message : String(e)}`);
        } finally {
          setBusy(false);
        }
        return;
      }
      if (cmd.action === "save") {
        await handleBriefExport(cmd.name);
        return;
      }
      if (cmd.action === "status") {
        const res = await window.gameFactory.briefBrainstormStatus();
        const d = res.data;
        if (!d?.exists) {
          appendAssistant("当前没有进行中的 Brief 策划会话。发送 `/brief` 或描述游戏想法开始。");
          return;
        }
        appendAssistant(
          `**Brief 会话**\n\n标题：${d.title || "（未定）"}\n资产数：${d.asset_count ?? 0}\n轮次：${d.message_count ?? 0}\n可导出：${d.ready_to_export ? "是" : "否"}`,
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
    if (cmd === "/godot") {
      await handleOpenGodot();
      return;
    }

    if (text.trim().startsWith("/")) {
      append("assistant", `未知指令。可用：/brief /doctor /plan /run /board /settings /godot`);
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

      <div className={`chat-layout ${sidePanel ? "side-open" : ""}`}>
        <section className="chat-column">
          <ChatView messages={messages} busy={busy} onSuggestion={handleSend} />
          <ChatInput
            disabled={busy}
            choices={brainstormChoices}
            readyToExport={brainstormReady}
            onSend={handleSend}
            onChoice={handleSend}
            onExportBrief={() => void handleBriefExport()}
          />
        </section>

        {sidePanel === "board" && (
          <BoardPanel
            manifest={selectedManifest}
            status={status}
            tasks={tasks}
            logs={logs}
            busy={busy}
            onRefresh={() => refreshManifest(selectedManifest)}
            onRun={handleRun}
          />
        )}

        {sidePanel === "settings" && <SettingsPanel busy={busy} />}
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
