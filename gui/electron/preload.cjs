const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("gameFactory", {
  getPaths: () => ipcRenderer.invoke("get-paths"),
  doctor: () => ipcRenderer.invoke("doctor"),
  toolchainCheck: () => ipcRenderer.invoke("toolchain-check"),
  toolchainInstall: (componentId) => ipcRenderer.invoke("toolchain-install", componentId),
  executorStatus: () => ipcRenderer.invoke("executor-status"),
  executorStep: (executorId, stepId) => ipcRenderer.invoke("executor-step", executorId, stepId),
  openExternal: (url) => ipcRenderer.invoke("open-external", url),
  listBriefs: () => ipcRenderer.invoke("list-briefs"),
  listManifests: () => ipcRenderer.invoke("list-manifests"),
  getManifestMeta: (manifestRel) => ipcRenderer.invoke("manifest-meta", manifestRel),
  findManifestForBrief: (briefRel) => ipcRenderer.invoke("find-manifest-for-brief", briefRel),
  readRepoText: (relPath) => ipcRenderer.invoke("read-repo-text", relPath),
  patchBriefProject: (relPath, projectPatch) =>
    ipcRenderer.invoke("patch-brief-project", relPath, projectPatch),
  listProjectDocs: (briefRel) => ipcRenderer.invoke("list-project-docs", briefRel),
  pipelinePlan: (opts) => ipcRenderer.invoke("pipeline-plan", opts),
  pipelineStatus: (manifestRel) => ipcRenderer.invoke("pipeline-status", manifestRel),
  pipelineRun: (manifestRel, jobs, runPrompts) =>
    ipcRenderer.invoke("pipeline-run", manifestRel, jobs, runPrompts),
  pipelineDiagnose: (manifestRel) => ipcRenderer.invoke("pipeline-diagnose", manifestRel),
  pipelineHeal: (manifestRel, apply) => ipcRenderer.invoke("pipeline-heal", manifestRel, apply),
  resolveBriefRel: (briefRel) => ipcRenderer.invoke("resolve-brief-rel", briefRel),
  visualTargetGenerate: (briefRel, candidates) =>
    ipcRenderer.invoke("visual-target-generate", briefRel, candidates),
  visualTargetList: (briefRel) => ipcRenderer.invoke("visual-target-list", briefRel),
  visualTargetPick: (briefRel, candidateId) =>
    ipcRenderer.invoke("visual-target-pick", briefRel, candidateId),
  visualTargetStatus: (briefRel) => ipcRenderer.invoke("visual-target-status", briefRel),
  openGodot: (projectRel) => ipcRenderer.invoke("open-godot", projectRel),
  getConfig: () => ipcRenderer.invoke("get-config"),
  saveConfig: (patch) => ipcRenderer.invoke("save-config", patch),
  initConfigFromExample: () => ipcRenderer.invoke("init-config-from-example"),
  openConfigFolder: () => ipcRenderer.invoke("open-config-folder"),
  pickFile: (opts) => ipcRenderer.invoke("pick-file", opts),
  getMediaPreview: (relPath, posterRel) => ipcRenderer.invoke("get-media-preview", relPath, posterRel),
  openMedia: (relPath) => ipcRenderer.invoke("open-media", relPath),
  listOutputMedia: (dirRel, limit) => ipcRenderer.invoke("list-output-media", dirRel, limit),
  hostChatStart: (sessionId, seed) => ipcRenderer.invoke("host-chat-start", sessionId, seed),
  hostChatTurn: (sessionId, message) => ipcRenderer.invoke("host-chat-turn", sessionId, message),
  hostChatReset: (sessionId, seed) => ipcRenderer.invoke("host-chat-reset", sessionId, seed),
  hostChatExport: (sessionId, outputRel) => ipcRenderer.invoke("host-chat-export", sessionId, outputRel),
  hostChatAutofix: (sessionId, maxRounds) =>
    ipcRenderer.invoke("host-chat-autofix", sessionId, maxRounds),
  hostChatStatus: (sessionId) => ipcRenderer.invoke("host-chat-status", sessionId),
  agentTurn: (opts) => ipcRenderer.invoke("agent-turn", opts),
  agentStatus: (role, sessionId) => ipcRenderer.invoke("agent-status", role, sessionId),
  handoffList: (status, targetInstanceId) =>
    ipcRenderer.invoke("handoff-list", status, targetInstanceId),
  runSafeAction: (command) => ipcRenderer.invoke("run-safe-action", command),
  productionDelta: (opts) => ipcRenderer.invoke("production-delta", opts),
  productionApplyDelta: (opts) => ipcRenderer.invoke("production-apply-delta", opts),
  onToolchainLog: (callback) => {
    const listener = (_event, payload) => callback(payload);
    ipcRenderer.on("toolchain-log", listener);
    return () => ipcRenderer.removeListener("toolchain-log", listener);
  },
  onPipelineLog: (callback) => {
    const listener = (_event, payload) => callback(payload);
    ipcRenderer.on("pipeline-log", listener);
    return () => ipcRenderer.removeListener("pipeline-log", listener);
  },
});
