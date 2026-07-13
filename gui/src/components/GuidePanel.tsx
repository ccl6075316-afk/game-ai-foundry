import { useState } from "react";
import { COMMAND_GUIDE } from "../settings/commandGuide";

export function GuidePanel() {
  const [sectionId, setSectionId] = useState(COMMAND_GUIDE[0]?.id || "workflow");

  const section = COMMAND_GUIDE.find((s) => s.id === sectionId) || COMMAND_GUIDE[0];

  const copyCommand = async (cmd: string) => {
    try {
      await navigator.clipboard.writeText(cmd);
    } catch {
      /* ignore */
    }
  };

  return (
    <aside className="side-panel guide-panel">
      <header className="side-panel__head">
        <h2>命令指南</h2>
        <p className="side-panel__sub">GUI 对话指令与 CLI 命令速查（在 cli/ 目录执行）</p>
      </header>

      <nav className="guide-nav" aria-label="指南分类">
        {COMMAND_GUIDE.map((s) => (
          <button
            key={s.id}
            type="button"
            className={`guide-nav__item ${sectionId === s.id ? "active" : ""}`}
            onClick={() => setSectionId(s.id)}
          >
            {s.title}
          </button>
        ))}
      </nav>

      {section && (
        <div className="guide-content">
          {section.intro && <p className="guide-intro">{section.intro}</p>}
          <ul className="guide-commands">
            {section.commands.map((item) => (
              <li key={`${section.id}-${item.command}`} className="guide-cmd">
                <div className="guide-cmd__head">
                  <strong>{item.title}</strong>
                  <button
                    type="button"
                    className="btn btn--ghost btn--sm"
                    onClick={() => void copyCommand(item.command)}
                  >
                    复制
                  </button>
                </div>
                <code className="guide-cmd__code">{item.command}</code>
                <p className="guide-cmd__desc">{item.description}</p>
                {item.note && <p className="guide-cmd__note">{item.note}</p>}
              </li>
            ))}
          </ul>
        </div>
      )}
    </aside>
  );
}
