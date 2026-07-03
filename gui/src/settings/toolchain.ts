/** Toolchain component from `gamefactory setup check --json`. */
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

export const GODOT_DOWNLOAD_URL = "https://godotengine.org/download";
export const DOTNET_DOWNLOAD_URL = "https://dotnet.microsoft.com/download";

export function missingComponents(report: ToolchainReport): ToolchainComponent[] {
  return report.components.filter((c) => !c.available);
}

export function autoInstallable(report: ToolchainReport): ToolchainComponent[] {
  return missingComponents(report).filter((c) => c.action === "auto" || c.action === "pip");
}
