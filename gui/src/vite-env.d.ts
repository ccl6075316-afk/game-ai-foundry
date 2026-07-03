export interface PathsInfo {
  repoRoot: string;
  cliDir: string;
  python: string;
  isDev: boolean;
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
  action: "auto" | "download_link" | "pip";
  download_url?: string;
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
  host?: {
    api_key?: string | null;
    model?: string;
    api_base?: string;
    proxy?: string;
  };
  image?: {
    api_key?: string;
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
    api_key?: string;
    model?: string;
    api_base?: string;
  };
  godot?: {
    engine_path?: string;
  };
  agents?: {
    orchestrator?: { executor?: string; skill?: string };
    "godot-developer"?: { executor?: string; skill?: string };
    "prompt-crafter"?: { executor?: string; skill?: string };
  };
}

export interface ConfigInfo {
  path: string;
  exists: boolean;
  data: {
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
      briefBrainstormStart: (seed?: string) => Promise<CliResult<import("./chat/types").BriefBrainstormResult>>;
      briefBrainstormTurn: (message: string) => Promise<CliResult<import("./chat/types").BriefBrainstormResult>>;
      briefBrainstormReset: (seed?: string) => Promise<CliResult<import("./chat/types").BriefBrainstormResult>>;
      briefBrainstormExport: (outputRel: string) => Promise<
        CliResult<{ brief_path?: string; brief?: Record<string, unknown> }>
      >;
      briefBrainstormStatus: () => Promise<CliResult<import("./chat/types").BriefBrainstormStatus>>;
      onPipelineLog: (cb: (payload: { line: string; stream: string }) => void) => () => void;
    };
  }
}

export {};
