import { useState } from "react";
import type { DoctorReport } from "../vite-env.d";
import type { ToolchainReport } from "../settings/toolchain";
import type { ExecutorSetupReport, ExecutorId } from "../settings/executorsSetup";
import type { SettingsTab } from "../settings/sections";
import { SettingsPanel } from "./SettingsPanel";
import { AgentSettingsView } from "./settings/AgentSettingsView";
import { ProviderSettingsView } from "./settings/ProviderSettingsView";
import { EnvPanel } from "./EnvPanel";
import { GuidePanel } from "./GuidePanel";

export type SettingsPageTab = SettingsTab | "env" | "guide";

const PAGE_TABS: { id: SettingsPageTab; label: string }[] = [
  { id: "providers", label: "Provider" },
  { id: "agents", label: "Agent" },
  { id: "local", label: "本机" },
  { id: "env", label: "环境" },
  { id: "guide", label: "指南" },
];

interface Props {
  initialTab?: SettingsPageTab;
  onClose: () => void;
  busy: boolean;
  toolchain: ToolchainReport | null;
  executorSetup: ExecutorSetupReport | null;
  doctor: DoctorReport | null;
  scanning: boolean;
  installing: string | null;
  executorBusy: string | null;
  installLog: string[];
  onRefreshEnv: () => void;
  onInstall: (id: string) => void;
  onInstallAll: () => void;
  onExecutorStep: (executorId: ExecutorId, stepId: string) => void;
  onOpenExternal: (url: string) => void;
}

export function SettingsPage({
  initialTab = "providers",
  onClose,
  busy,
  toolchain,
  executorSetup,
  doctor,
  scanning,
  installing,
  executorBusy,
  installLog,
  onRefreshEnv,
  onInstall,
  onInstallAll,
  onExecutorStep,
  onOpenExternal,
}: Props) {
  const [tab, setTab] = useState<SettingsPageTab>(initialTab);
  const [providerRevision, setProviderRevision] = useState(0);

  return (
    <div className="settings-page">
      <header className="settings-page__head">
        <button type="button" className="btn btn--ghost" onClick={onClose}>
          ← 返回聊天
        </button>
        <nav className="settings-page__tabs" aria-label="设置分类">
          {PAGE_TABS.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`settings-tab ${tab === item.id ? "active" : ""}`}
              onClick={() => setTab(item.id)}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </header>

      <div className="settings-page__body">
        {tab === "providers" && (
          <ProviderSettingsView
            busy={busy}
            onSaved={() => setProviderRevision((n) => n + 1)}
          />
        )}

        {tab === "agents" && (
          <AgentSettingsView busy={busy} providerAccountsRevision={providerRevision} />
        )}

        {tab === "local" && (
          <SettingsPanel busy={busy} embedded forcedTab="local" />
        )}

        {tab === "env" && (
          <EnvPanel
            embedded
            toolchain={toolchain}
            executorSetup={executorSetup}
            doctor={doctor}
            scanning={scanning}
            installing={installing}
            executorBusy={executorBusy}
            installLog={installLog}
            onRefresh={onRefreshEnv}
            onInstall={onInstall}
            onInstallAll={onInstallAll}
            onExecutorStep={onExecutorStep}
            onOpenExternal={onOpenExternal}
            onOpenSettings={() => setTab("providers")}
          />
        )}

        {tab === "guide" && <GuidePanel embedded />}
      </div>
    </div>
  );
}
