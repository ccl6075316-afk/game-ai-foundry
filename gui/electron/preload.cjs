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
  pipelinePlan: (opts) => ipcRenderer.invoke("pipeline-plan", opts),
  pipelineStatus: (manifestRel) => ipcRenderer.invoke("pipeline-status", manifestRel),
  pipelineRun: (manifestRel, jobs, runPrompts) =>
    ipcRenderer.invoke("pipeline-run", manifestRel, jobs, runPrompts),
  openGodot: (projectRel) => ipcRenderer.invoke("open-godot", projectRel),
  getConfig: () => ipcRenderer.invoke("get-config"),
  saveConfig: (patch) => ipcRenderer.invoke("save-config", patch),
  initConfigFromExample: () => ipcRenderer.invoke("init-config-from-example"),
  openConfigFolder: () => ipcRenderer.invoke("open-config-folder"),
  pickFile: (opts) => ipcRenderer.invoke("pick-file", opts),
  getMediaPreview: (relPath, posterRel) => ipcRenderer.invoke("get-media-preview", relPath, posterRel),
  openMedia: (relPath) => ipcRenderer.invoke("open-media", relPath),
  listOutputMedia: (dirRel, limit) => ipcRenderer.invoke("list-output-media", dirRel, limit),
  briefBrainstormStart: (seed) => ipcRenderer.invoke("brief-brainstorm-start", seed),
  briefBrainstormTurn: (message) => ipcRenderer.invoke("brief-brainstorm-turn", message),
  briefBrainstormReset: (seed) => ipcRenderer.invoke("brief-brainstorm-reset", seed),
  briefBrainstormExport: (outputRel) => ipcRenderer.invoke("brief-brainstorm-export", outputRel),
  briefBrainstormStatus: () => ipcRenderer.invoke("brief-brainstorm-status"),
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
