/// <reference types="vite/client" />

export interface PathsInfo {
  repoRoot: string;
  cliDir: string;
  python: string;
  isDev: boolean;
  isPackaged?: boolean;
  appVersion?: string;
}

export type AppUpdatePhase =
  | "idle"
  | "checking"
  | "available"
  | "not-available"
  | "downloading"
  | "downloaded"
  | "error"
  | "unsupported";

export interface AppUpdateStatus {
  phase: AppUpdatePhase;
  currentVersion: string;
  availableVersion?: string;
  percent?: number;
  message?: string;
  releaseName?: string;
  releaseNotes?: string;
  error?: string;
}

export interface CliResult<T = unknown> {
  exitCode: number;
  stdout: string;
  stderr: string;
  data?: T;
  aborted?: boolean;
}

export interface BriefItem {
  id: string;
  path: string;
  label: string;
  mtime?: number;
  /** ready = brief.json exists; draft = project folder without exported brief yet */
  status?: "ready" | "draft";
}

export interface ExternalProjectEntry {
  id: string;
  display_name: string;
  root_abs: string;
  godot_rel: string;
  brief_rel: string;
  added_at?: string;
}

export interface ExternalProjectDetectLayout {
  godot_rel?: string | null;
  has_brief?: boolean;
  godot_abs?: string | null;
  brief_abs?: string;
  errors?: string[];
}

export interface ExternalProjectOpenResult {
  ok: boolean;
  canceled?: boolean;
  error?: string;
  exitCode?: number;
  entry?: ExternalProjectEntry;
  briefRel?: string;
  detect?: ExternalProjectDetectLayout | null;
}

export interface ExternalProjectsListResult {
  ok: boolean;
  exitCode?: number;
  projects: ExternalProjectEntry[];
  count: number;
}

export interface ExternalProjectRemoveResult {
  ok: boolean;
  exitCode?: number;
  error?: string;
  stderr?: string;
}

export interface ManifestMeta {
  brief?: string;
  output_dir?: string;
  godot_project?: string;
  project_title?: string;
  task_count?: number;
  counts?: Record<string, number>;
}

export interface ManifestMatch {
  path: string;
  label?: string;
  mtime?: number;
  meta?: ManifestMeta | null;
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

export interface AssetReviewRow {
  row_id: string;
  asset_name: string;
  kit_item_slug?: string | null;
  label: string;
  type: string;
  usage: string;
  preview_path_repo: string | null;
  canonical_path_repo: string | null;
  stages_summary?: string;
  review: {
    status: "pending" | "accepted" | "replaced";
    source: "pipeline" | "regenerate" | "local_file";
    updated_at: string;
    note: string;
  };
}

export interface AssetReviewAcceptResult {
  ok?: boolean;
  row_id?: string;
  review?: AssetReviewRow["review"];
}

export interface AssetReviewReplaceResult {
  ok?: boolean;
  row_id?: string;
  path_repo?: string;
  review?: AssetReviewRow["review"];
}

export interface AssetReviewRegeneratePlan {
  reset_task_id?: string | null;
  commands?: string[];
}

export interface AssetReviewRegenerateResult {
  plan?: AssetReviewRegeneratePlan;
  reset?: CliResult;
  run?: unknown;
}

export interface ConfigPatch {
  /** Top-level HTTP proxy (authoritative for CLI); null clears */
  proxy?: string | null;
  provider_accounts?: Record<string, unknown>;
  video_accounts?: Record<string, unknown>;
  host?: {
    provider?: string;
    api_key?: string | null;
    model?: string;
    api_base?: string;
    /** Prefer top-level proxy; null clears legacy nested proxy */
    proxy?: string | null;
  };
  image?: {
    provider?: string;
    use_text_provider?: boolean;
    api_key?: string | null;
    model?: string;
    /** Provider account for bulk stills; omit/null → same as provider */
    bulk_provider?: string | null;
    /** Cheaper model for icon_kit items / generate_tier=bulk; null clears */
    bulk_model?: string | null;
    /** Prefer top-level proxy; null clears legacy nested proxy */
    proxy?: string | null;
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
  /** Local toolchain paths + optional GitHub download mirror */
  toolchain?: {
    bin_dir?: string;
    godot_dir?: string;
    dotnet_dir?: string;
    /** When true, prefix GitHub downloads with a reverse-proxy mirror (default false) */
    download_mirror?: boolean;
    /** Mirror URL prefix, default https://ghproxy.net/ */
    download_mirror_prefix?: string;
  };
  agents?: {
    brief?: { executor?: string; skill?: string; provider?: string; model?: string | null };
    it?: { executor?: string; skill?: string; provider?: string; model?: string | null };
    orchestrator?: {
      executor?: string;
      skill?: string;
      provider?: string;
      model?: string | null;
      use_third_party?: boolean;
    };
    "godot-developer"?: {
      executor?: string;
      skill?: string;
      provider?: string;
      model?: string | null;
      use_third_party?: boolean;
    };
    "prompt-crafter"?: { executor?: string; skill?: string };
    /** Foundry provider_accounts id synced into Hermes (~/.hermes) */
    hermes_provider?: string;
    executors?: {
      pi?: { provider?: string; model?: string | null };
      hermes?: { provider?: string; model?: string | null };
      codex?: {
        provider?: string;
        model?: string | null;
        use_third_party?: boolean;
      };
      cursor?: Record<string, never>;
    };
    instances?: Record<
      string,
      {
        role_kind?: string;
        executor?: string;
        provider?: string | null;
        model?: string | null;
        use_third_party?: boolean;
      } | null
    >;
  };
}

export interface ConfigInfo {
  path: string;
  exists: boolean;
  data: {
    proxy?: string;
    provider_accounts?: Record<string, unknown>;
    video_accounts?: Record<string, unknown>;
    host?: Record<string, unknown>;
    image?: Record<string, unknown>;
    prompt?: Record<string, unknown>;
    code?: Record<string, unknown>;
    video?: Record<string, unknown>;
    godot?: Record<string, unknown>;
    toolchain?: Record<string, unknown>;
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
      executorModels: (
        executorId: "codex" | "cursor",
      ) => Promise<
        CliResult<{
          ok?: boolean;
          executor?: string;
          models?: Array<{ id: string; label?: string }>;
          hint?: string | null;
          error?: string | null;
          source?: string | null;
        }>
      >;
      providerModels: (
        providerId: string,
      ) => Promise<
        CliResult<{
          ok?: boolean;
          models?: Array<{ id: string; label?: string }>;
          error?: string | null;
          source?: string | null;
        }>
      >;
      executorStep: (
        executorId: import("./settings/executorsSetup").ExecutorId,
        stepId: string,
        opts?: { instanceId?: string; provider?: string },
      ) => Promise<CliResult<{ ok?: boolean; error?: string; message?: string; skipped?: boolean; status?: import("./settings/executorsSetup").ExecutorSetupInfo }>>;
      openExternal: (url: string) => Promise<{ ok: boolean; error?: string }>;
      listBriefs: () => Promise<BriefItem[]>;
      listManifests: () => Promise<BriefItem[]>;
      getManifestMeta: (manifestRel: string) => Promise<ManifestMeta | null>;
      findManifestForBrief: (briefRel: string) => Promise<ManifestMatch | null>;
      readRepoText: (relPath: string) => Promise<{
        ok: boolean;
        path?: string;
        text?: string;
        error?: string;
      }>;
      patchBriefProject: (
        relPath: string,
        projectPatch: Record<string, unknown>,
      ) => Promise<{
        ok: boolean;
        path?: string;
        changed?: string[];
        skipped?: boolean;
        error?: string;
      }>;
      listProjectDocs: (briefRel?: string | null) => Promise<
        Array<{
          path: string;
          label: string;
          kind: "brief" | "markdown" | "json";
        }>
      >;
      ensureProject: (slug: string) => Promise<{
        ok: boolean;
        error?: string;
        slug?: string;
        projectRootRel?: string;
        briefRel?: string;
        guideRel?: string;
        existed?: boolean;
      }>;
      externalProjectOpen: () => Promise<ExternalProjectOpenResult>;
      externalProjectsList: () => Promise<ExternalProjectsListResult>;
      externalProjectRemove: (extId: string) => Promise<ExternalProjectRemoveResult>;
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
      pipelineDiagnose: (manifestRel: string) => Promise<CliResult & { data?: any }>;
      pipelineHeal: (manifestRel: string, apply?: boolean) => Promise<CliResult & { data?: any }>;
      assetsReviewList: (
        assetsManifestRel: string | null,
        pipelineManifestRel?: string | null,
      ) => Promise<CliResult<{ rows: AssetReviewRow[] }>>;
      assetsReviewAccept: (
        assetsManifestRel: string,
        assetName: string,
        itemSlug?: string | null,
      ) => Promise<CliResult<AssetReviewAcceptResult>>;
      assetsReviewReplace: (
        assetsManifestRel: string,
        assetName: string,
        itemSlug: string | null | undefined,
        absFilePath: string,
      ) => Promise<CliResult<AssetReviewReplaceResult>>;
      assetsReviewRegenerate: (
        pipelineManifestRel: string,
        assetName: string,
        itemSlug?: string | null,
        jobs?: number,
      ) => Promise<CliResult<AssetReviewRegenerateResult>>;
      resolveBriefRel: (briefRel: string) => Promise<{
        input: string;
        path: string;
        exists: boolean;
      }>;
      visualTargetGenerate: (
        briefRel: string,
        candidates?: number,
        sceneId?: string | null,
      ) => Promise<
        CliResult<{
          manifest_path?: string;
          scene_id?: string | null;
          candidates?: Array<{
            id?: string;
            label?: string;
            path?: string;
            status?: string;
          }>;
        }>
      >;
      visualTargetList: (briefRel: string, sceneId?: string | null) => Promise<CliResult>;
      visualTargetPick: (
        briefRel: string,
        candidateId: string,
        sceneId?: string | string[] | null,
        manifestPath?: string | null,
      ) => Promise<
        CliResult<{
          visual_reference?: string;
          selected_id?: string;
          scene_id?: string | null;
          scene_ids?: string[];
          auto_matched_scene_ids?: string[];
          auto_match_method?: string | null;
        }>
      >;
      visualTargetAssign: (
        briefRel: string,
        sceneIds: string | string[],
        opts?: {
          fromScene?: string;
          fromGlobal?: boolean;
          ref?: string;
        },
      ) => Promise<
        CliResult<{
          visual_reference?: string;
          scene_ids?: string[];
          skipped_scene_ids?: string[];
          source?: string;
        }>
      >;
      visualTargetStatus: (
        briefRel: string,
        sceneId?: string | null,
      ) => Promise<{
        ok: boolean;
        ready: boolean;
        global_ready?: boolean;
        visual_reference?: string;
        path_shaped?: boolean;
        file_ok?: boolean;
        selected_id?: string | null;
        scene_id?: string | null;
        scenes?: Array<{
          id: string;
          title?: string;
          visual_reference?: string;
          ready?: boolean;
        }>;
        candidates?: Array<{ id: string; label?: string; path?: string; status?: string }>;
        error?: string;
      }>;
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
        instanceId?: string,
        briefRel?: string | null,
      ) => Promise<CliResult<import("./chat/types").HostChatResult>>;
      hostChatTurn: (
        sessionId: string,
        message: string,
        instanceId?: string,
        briefRel?: string | null,
      ) => Promise<CliResult<import("./chat/types").HostChatResult>>;
      hostChatReset: (
        sessionId: string,
        seed?: string,
        instanceId?: string,
        briefRel?: string | null,
      ) => Promise<CliResult<import("./chat/types").HostChatResult>>;
      hostChatBind: (
        sessionId: string,
        briefRel: string,
      ) => Promise<
        CliResult<{
          project_slug?: string;
          bound_brief_rel?: string;
          asset_count?: number;
          draft_brief?: import("./chat/types").HostChatDraftBrief | null;
          title?: string;
        }>
      >;
      hostChatExport: (
        sessionId: string,
        outputRel: string,
        instanceId?: string,
      ) => Promise<
        CliResult<{
          brief_path?: string;
          brief_rel?: string;
          brief?: Record<string, unknown>;
          session_id?: string;
          zh_doc_path?: string;
          zh_doc_rel?: string;
          zh_doc_name?: string;
          zh_doc_mode?: string;
          zh_doc_error?: string;
        }>
      >;
      hostChatZhDoc: (
        sessionId: string,
        briefRel: string,
        skeletonOnly?: boolean,
      ) => Promise<
        CliResult<{
          zh_doc_path?: string;
          zh_doc_rel?: string;
          zh_doc_name?: string;
          zh_doc_mode?: string;
          brief_rel?: string;
        }>
      >;
      hostChatUiWireframe: (
        sessionId: string,
        briefRel: string,
      ) => Promise<
        CliResult<{
          ok?: boolean;
          path?: string;
          panel_count?: number;
          error?: string;
          ui_wireframe_rel?: string;
          brief_rel?: string;
          session_id?: string;
        }>
      >;
      hostChatAutofix: (
        sessionId: string,
        maxRounds?: number,
        instanceId?: string,
      ) => Promise<
        CliResult<{
          ok?: boolean;
          reason?: string;
          rounds_run?: number;
          max_rounds?: number;
          gaps?: string[];
          rounds?: Array<{
            round?: number;
            gaps_before?: string[];
            gaps_after?: string[];
            assistant_message?: string;
            gap_count_before?: number;
            gap_count_after?: number;
          }>;
          draft_brief?: import("./chat/types").HostChatDraftBrief | null;
          ready_to_export?: boolean;
          assistant_message?: string;
          session_id?: string;
        } & import("./chat/types").HostChatStatus>
      >;
      hostChatMakeability: (
        sessionId: string,
        instanceId?: string,
      ) => Promise<
        CliResult<{
          ok?: boolean;
          review?: import("./chat/types").MakeabilityReview;
          intent_count?: number;
          detail_count?: number;
          repair_count?: number;
          ready_to_export?: boolean;
          assistant_message?: string;
          session_id?: string;
        } & import("./chat/types").HostChatStatus>
      >;
      hostChatMakeabilityAnswer: (
        sessionId: string,
        answers: Array<{ gap_id: string; choice?: string; note?: string }>,
        instanceId?: string,
      ) => Promise<
        CliResult<
          import("./chat/types").MakeabilityAnswerResult & {
            assistant_message?: string;
            draft_brief?: import("./chat/types").HostChatDraftBrief | null;
            review?: import("./chat/types").MakeabilityReview;
            session_id?: string;
          } & import("./chat/types").HostChatStatus
        >
      >;
      hostChatEnrich: (
        sessionId: string,
        hint?: string | null,
        instanceId?: string,
      ) => Promise<
        CliResult<{
          ok?: boolean;
          summary?: string;
          assistant_message?: string;
          fingerprint?: string;
          asset_count?: number;
          ready_to_export?: boolean;
          draft_brief?: import("./chat/types").HostChatDraftBrief | null;
          session_id?: string;
        } & import("./chat/types").HostChatStatus>
      >;
      hostChatTopicBrainstorm: (
        sessionId: string,
        topic: string,
        constraints?: string | null,
        multiModel?: boolean,
        instanceId?: string,
      ) => Promise<
        CliResult<{
          ok?: boolean;
          mode?: string;
          proposal_count?: number;
          assistant_message?: string;
          brainstorm_result?: {
            topic?: string;
            mode?: string;
            proposals?: Array<{
              id?: string;
              role?: string;
              title?: string;
              bullets?: string[];
              model?: string | null;
            }>;
          };
          session_id?: string;
        }>
      >;
      hostChatBrainstormApply: (
        sessionId: string,
        proposalIds: string[],
        fuse?: boolean,
        instanceId?: string,
      ) => Promise<
        CliResult<{
          ok?: boolean;
          summary?: string;
          assistant_message?: string;
          fingerprint?: string;
          asset_count?: number;
          applied_ids?: string[];
          ready_to_export?: boolean;
          draft_brief?: import("./chat/types").HostChatDraftBrief | null;
          session_id?: string;
        } & import("./chat/types").HostChatStatus>
      >;
      hostChatStatus: (sessionId: string) => Promise<CliResult<import("./chat/types").HostChatStatus>>;
      agentTurn: (opts: {
        role: "product_host" | "programmer" | "it" | "advisor";
        sessionId: string;
        message: string;
        executor?: "hermes" | "codex" | "cursor" | "pi";
        brief?: string;
        progress?: string;
        instanceId?: string;
        targetInstanceId?: string;
        rosterJson?: string;
        timeout?: number;
        /** IT: pre-approve FOUNDRY_TOOL mutates for this session (default true). */
        piSessionTrust?: boolean;
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
            gui_hints?: string[];
            cli_hints?: string[];
          };
        }>
      >;
      decideToolPermission: (
        permissionId: string,
        decision: "once" | "turn" | "session" | "deny",
      ) => Promise<{ ok?: boolean }>;
      setPiSessionTrust: (
        sessionId: string,
        trusted: boolean,
      ) => Promise<{ ok?: boolean; trusted?: boolean; error?: string }>;
      stopAgentAcpInstance: (instanceId: string) => Promise<{ ok?: boolean; error?: string }>;
      chatStop: (
        instanceId: string,
      ) => Promise<{ ok?: boolean; aborted?: boolean; killedCli?: boolean; stoppedAcp?: boolean; error?: string }>;
      appUpdateStatus: () => Promise<AppUpdateStatus>;
      appUpdateCheck: () => Promise<AppUpdateStatus>;
      appUpdateInstall: () => Promise<{ ok?: boolean; error?: string }>;
      onAppUpdateStatus: (callback: (status: AppUpdateStatus) => void) => () => void;
      onToolPermission: (
        callback: (payload: {
          permissionId: string;
          sessionId: string;
          turnId?: string;
          instanceId?: string;
          argvSummary: string;
          argv?: string[];
          source?: "pi" | "cursor_acp" | "hermes_acp" | "codex_app_server";
        }) => void,
      ) => () => void;
      onToolPermissionResolved: (
        callback: (payload: { permissionId: string; decision: string }) => void,
      ) => () => void;
      agentStatus: (
        role: "product_host" | "programmer" | "it" | "advisor",
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
