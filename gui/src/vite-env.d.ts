export interface PathsInfo {
  repoRoot: string;
  cliDir: string;
  python: string;
  isDev: boolean;
  isPackaged?: boolean;
}

export interface CliResult<T = unknown> {
  exitCode: number;
  stdout: string;
  stderr: string;
  data?: T;
}

export interface BriefItem {
  id: string;
  path: string;
  label: string;
  mtime?: number;
}

export interface ManifestMeta {
  brief?: string;
  output_dir?: string;
  godot_project?: string;
  project_title?: string;
}

export interface ToolchainComponent {
  id: string;
  label: string;
  description: string;
  required: boolean;
  action: "auto" | "download_link" | "pip" | "install_guide";
  download_url?: string;
  install_cmd?: string;
  available: boolean;
  path?: string | null;
}

export interface ToolchainReport {
  toolchain_root: string;
  bin_dir: string;
  components: ToolchainComponent[];
  missing_required: string[];
  missing_optional: string[];
  needs_attention: boolean;
}

export interface DoctorReport {
  capabilities: Record<string, boolean>;
  executors: Record<
    string,
    { available: boolean; cli?: string; hints?: string[]; reason?: string }
  >;
  config: {
    path: string;
    exists: boolean;
    openrouter_key: string;
    seedance_key: string;
    godot_engine_path: string;
  };
  agents: Record<
    string,
    {
      role: string;
      executor: string;
      configured_executor?: string;
      executor_available?: boolean;
      suggested_executor?: string;
      action_required?: boolean;
    }
  >;
}

export interface PipelineTask {
  id: string;
  asset: string;
  step: string;
  role: string;
  status: string;
  layer: number;
  command?: string;
}

export interface PipelineStatus {
  brief?: string;
  total?: number;
  counts?: Record<string, number>;
  done?: boolean;
  ready_ids?: string[];
  failed_ids?: string[];
}

export interface ConfigPatch {
  provider_accounts?: Record<string, unknown>;
  video_accounts?: Record<string, unknown>;
  host?: {
    provider?: string;
    api_key?: string | null;
    model?: string;
    api_base?: string;
    proxy?: string;
  };
  image?: {
    provider?: string;
    use_text_provider?: boolean;
    api_key?: string | null;
    model?: string;
    proxy?: string;
    api_base?: string;
  };
  prompt?: {
    api_key?: string | null;
    model?: string;
    proxy?: string;
    api_base?: string | null;
  };
  code?: {
    api_key?: string | null;
    model?: string;
    api_base?: string | null;
    proxy?: string;
  };
  video?: {
    provider?: string;
    api_key?: string | null;
    model?: string;
    api_base?: string;
  };
  godot?: {
    engine_path?: string;
  };
  agents?: {
    orchestrator?: { executor?: string; skill?: string; provider?: string };
    "godot-developer"?: { executor?: string; skill?: string; provider?: string };
    "prompt-crafter"?: { executor?: string; skill?: string };
    /** Foundry provider_accounts id synced into Hermes (~/.hermes) */
    hermes_provider?: string;
  };
}

export interface ConfigInfo {
  path: string;
  exists: boolean;
  data: {
    provider_accounts?: Record<string, unknown>;
    video_accounts?: Record<string, unknown>;
    host?: Record<string, unknown>;
    image?: Record<string, unknown>;
    prompt?: Record<string, unknown>;
    code?: Record<string, unknown>;
    video?: Record<string, unknown>;
    godot?: Record<string, unknown>;
    agents?: Record<string, unknown>;
    matting?: Record<string, unknown>;
  };
}

export interface SaveConfigResult {
  ok: boolean;
  path?: string;
  error?: string;
}

declare global {
  interface Window {
    gameFactory: {
      getPaths: () => Promise<PathsInfo>;
      doctor: () => Promise<CliResult<DoctorReport>>;
      toolchainCheck: () => Promise<CliResult<ToolchainReport>>;
      toolchainInstall: (componentId: string) => Promise<CliResult<{ ok?: boolean; error?: string }>>;
      executorStatus: () => Promise<CliResult<import("./settings/executorsSetup").ExecutorSetupReport>>;
      executorStep: (
        executorId: import("./settings/executorsSetup").ExecutorId,
        stepId: string,
      ) => Promise<CliResult<{ ok?: boolean; error?: string; message?: string; status?: import("./settings/executorsSetup").ExecutorSetupInfo }>>;
      openExternal: (url: string) => Promise<{ ok: boolean; error?: string }>;
      listBriefs: () => Promise<BriefItem[]>;
      listManifests: () => Promise<BriefItem[]>;
      getManifestMeta: (manifestRel: string) => Promise<ManifestMeta | null>;
      pipelinePlan: (opts: {
        briefRel: string;
        manifestRel: string;
        outputDirRel: string;
        godotProjectRel: string;
      }) => Promise<CliResult>;
      pipelineStatus: (manifestRel: string) => Promise<{
        exitCode: number;
        status: PipelineStatus;
        tasks: PipelineTask[];
      }>;
      pipelineRun: (manifestRel: string, jobs: number, runPrompts?: boolean) => Promise<CliResult>;
      openGodot: (projectRel: string) => Promise<CliResult>;
      getConfig: () => Promise<ConfigInfo>;
      saveConfig: (patch: ConfigPatch) => Promise<SaveConfigResult>;
      initConfigFromExample: () => Promise<ConfigInfo>;
      openConfigFolder: () => Promise<{ ok: boolean }>;
      pickFile: (opts?: {
        title?: string;
        filters?: { name: string; extensions: string[] }[];
      }) => Promise<string | null>;
      getMediaPreview: (
        relPath: string,
        posterRel?: string,
      ) => Promise<{
        kind: "image" | "video";
        name: string;
        path: string;
        previewUrl?: string;
        posterUrl?: string;
      } | null>;
      openMedia: (relPath: string) => Promise<{ ok: boolean; path?: string; error?: string }>;
      listOutputMedia: (
        dirRel: string,
        limit?: number,
      ) => Promise<
        Array<{
          path: string;
          kind: "image" | "video";
          label?: string;
          posterPath?: string;
        }>
      >;
      hostChatStart: (
        sessionId: string,
        seed?: string,
      ) => Promise<CliResult<import("./chat/types").HostChatResult>>;
      hostChatTurn: (
        sessionId: string,
        message: string,
      ) => Promise<CliResult<import("./chat/types").HostChatResult>>;
      hostChatReset: (
        sessionId: string,
        seed?: string,
      ) => Promise<CliResult<import("./chat/types").HostChatResult>>;
      hostChatExport: (
        sessionId: string,
        outputRel: string,
      ) => Promise<CliResult<{ brief_path?: string; brief?: Record<string, unknown>; session_id?: string }>>;
      hostChatStatus: (sessionId: string) => Promise<CliResult<import("./chat/types").HostChatStatus>>;
      agentTurn: (opts: {
        role: "product_host" | "programmer";
        sessionId: string;
        message: string;
        executor?: "hermes" | "codex" | "cursor";
        brief?: string;
        progress?: string;
        instanceId?: string;
        targetInstanceId?: string;
        rosterJson?: string;
        timeout?: number;
      }) => Promise<
        CliResult<{
          ok?: boolean;
          status?: string;
          error?: string;
          assistant_message?: string;
          executor?: string;
          session_id?: string;
          message_count?: number;
          dispatch?: {
            applied?: boolean;
            triage?: string;
            handoff_path?: string;
            handoff_id?: string;
            handoff_done?: string;
            progress_note_written?: boolean;
            task_updated?: string;
            task_done?: string;
            dispatch_to?: string;
            target_instance_id?: string;
            next_actions?: string[];
          };
        }>
      >;
      agentStatus: (
        role: "product_host" | "programmer",
        sessionId: string,
      ) => Promise<CliResult<{ exists?: boolean; message_count?: number; executor?: string }>>;
      handoffList: (
        status?: string,
        targetInstanceId?: string | null,
      ) => Promise<
        CliResult<{
          handoffs?: Array<{
            id?: string;
            path?: string;
            status?: string;
            triage?: string;
            title?: string;
            task_id?: string;
            target_instance_id?: string | null;
            cli_hints?: string[];
          }>;
          count?: number;
        }>
      >;
      runSafeAction: (command: string) => Promise<
        CliResult<{
          ok?: boolean;
          error?: string;
          argv?: string[];
          label?: string;
          exit_code?: number;
          stdout?: string;
          stderr?: string;
        }>
      >;
      productionDelta: (opts: {
        changeId: string;
        intent: string;
        tasks?: string[];
        output?: string;
      }) => Promise<
        CliResult<{ ok?: boolean; path?: string; delta?: Record<string, unknown> }>
      >;
      productionApplyDelta: (opts: {
        delta: string;
        production: string;
        progress?: string;
        dryRun?: boolean;
      }) => Promise<
        CliResult<{
          ok?: boolean;
          change_id?: string;
          tasks_added?: string[];
          progress_tasks_added?: string[];
        }>
      >;
      onPipelineLog: (cb: (payload: { line: string; stream: string }) => void) => () => void;
      onToolchainLog?: (cb: (payload: { line: string }) => void) => () => void;
    };
  }
}

export {};
