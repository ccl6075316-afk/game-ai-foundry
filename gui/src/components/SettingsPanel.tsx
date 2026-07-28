import { useCallback, useEffect, useState, type ReactNode } from "react";
import type { ConfigInfo, ConfigPatch } from "../vite-env.d";
import {
  GODOT_SECTION,
  type SettingsSectionMeta,
  type SettingsTab,
} from "../settings/sections";
import { GODOT_DOWNLOAD_URL } from "../settings/toolchain";

interface Props {
  busy: boolean;
  onSaved?: () => void;
  /** Full-page settings: no side-panel shell or internal tab bar */
  embedded?: boolean;
  /** When set (typically with embedded), only render this tab's content */
  forcedTab?: SettingsTab;
}

interface FormState {
  godotPath: string;
}

function fromConfig(data: ConfigInfo["data"]): FormState {
  const godot = data.godot || {};
  return {
    godotPath: String(godot.engine_path || ""),
  };
}

function toLocalPatch(form: FormState): ConfigPatch {
  return {
    godot: {
      engine_path: form.godotPath || undefined,
    },
  };
}

function SectionCard({
  meta,
  configured,
  statusOk = "已填写",
  statusWarn = "未填写",
  children,
}: {
  meta: SettingsSectionMeta;
  configured?: boolean;
  statusOk?: string;
  statusWarn?: string;
  children: ReactNode;
}) {
  return (
    <section className="settings-card">
      <header className="settings-card__head">
        <div className="settings-card__title-row">
          <span className="settings-card__step">{meta.step}</span>
          <div>
            <h3 className="settings-card__title">{meta.title}</h3>
            <span className="settings-card__role-id">（{meta.roleId}）</span>
          </div>
          {configured !== undefined && (
            <span className={`settings-card__status ${configured ? "ok" : "warn"}`}>
              {configured ? statusOk : statusWarn}
            </span>
          )}
        </div>
        <p className="settings-card__purpose">{meta.purpose}</p>
        {meta.note && <p className="settings-card__note">{meta.note}</p>}
      </header>
      <div className="settings-card__body">{children}</div>
    </section>
  );
}

export function SettingsPanel({ busy, onSaved, embedded = false, forcedTab }: Props) {
  const tab = forcedTab ?? "local";
  const [configInfo, setConfigInfo] = useState<ConfigInfo | null>(null);
  const [form, setForm] = useState<FormState>(() => fromConfig({}));
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const info = await window.gameFactory.getConfig();
      setConfigInfo(info);
      setForm(fromConfig(info.data));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const setField = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
    setMessage(null);
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      await window.gameFactory.getConfig();
      const patch = toLocalPatch(form);
      const res = await window.gameFactory.saveConfig(patch);
      if (!res.ok) throw new Error(res.error || "保存失败");

      setMessage("已保存");
      await load();
      onSaved?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  const handleInitExample = async () => {
    setSaving(true);
    setError(null);
    try {
      await window.gameFactory.initConfigFromExample();
      setMessage("已从示例创建，请填入你的账号密钥");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  const handleBrowseGodot = async () => {
    const picked = await window.gameFactory.pickFile({
      title: "选择 Godot 可执行文件",
      filters: [{ name: "Godot", extensions: ["exe"] }, { name: "All", extensions: ["*"] }],
    });
    if (picked) setField("godotPath", picked);
  };

  const disabled = busy || loading || saving;

  const Shell = embedded ? "div" : "aside";
  const shellClass = embedded
    ? "settings-panel settings-panel--embedded"
    : "side-panel settings-panel";

  return (
    <Shell className={shellClass}>
      {!embedded && (
        <div className="side-panel__head">
          <h2>设置</h2>
          <p className="hint">本机 Godot 等工具路径。</p>
        </div>
      )}

      {configInfo && (
        <button
          type="button"
          className="settings-path"
          onClick={() => void window.gameFactory.openConfigFolder()}
          title={configInfo.path}
        >
          <span className="settings-path__label">配置文件</span>
          <span className="settings-path__value mono">{configInfo.path}</span>
          <span className={`settings-path__status ${configInfo.exists ? "ok" : "missing"}`}>
            {configInfo.exists ? "已存在" : "未创建 — 可先点「从示例创建」"}
          </span>
        </button>
      )}

      {loading ? (
        <p className="hint">加载中…</p>
      ) : (
        <form
          className="settings-form"
          onSubmit={(e) => {
            e.preventDefault();
            void handleSave();
          }}
        >
          {tab === "local" && (
            <SectionCard meta={GODOT_SECTION} configured={Boolean(form.godotPath.trim())}>
              <label className="field">
                <span>Godot 可执行文件</span>
                <div className="field-row">
                  <input
                    type="text"
                    value={form.godotPath}
                    onChange={(e) => setField("godotPath", e.target.value)}
                    placeholder="Godot_v4.x_mono_console.exe"
                    disabled={disabled}
                  />
                  <button
                    type="button"
                    className="btn btn--secondary"
                    onClick={() => void handleBrowseGodot()}
                    disabled={disabled}
                  >
                    浏览
                  </button>
                </div>
                <span className="field-hint">用于打开工程、导入素材、检查项目是否正常</span>
              </label>
              <div className="field-row field-row--wrap">
                <button
                  type="button"
                  className="btn btn--secondary"
                  disabled={disabled}
                  onClick={() => void window.gameFactory.openExternal(GODOT_DOWNLOAD_URL)}
                >
                  下载 Godot .NET（官方）
                </button>
                <span className="field-hint">
                  选 <strong>.NET / Mono</strong> 版 zip，解压即用；Windows 填 <code>*_console.exe</code>
                </span>
              </div>
            </SectionCard>
          )}

          {error && <p className="settings-feedback settings-feedback--error">{error}</p>}
          {message && <p className="settings-feedback settings-feedback--ok">{message}</p>}

          <div className="settings-actions">
            {!configInfo?.exists && (
              <button
                type="button"
                className="btn btn--secondary"
                onClick={() => void handleInitExample()}
                disabled={disabled}
              >
                从示例创建
              </button>
            )}
            <button type="submit" className="btn btn--primary" disabled={disabled}>
              {saving ? "保存中…" : "保存设置"}
            </button>
          </div>
        </form>
      )}
    </Shell>
  );
}
