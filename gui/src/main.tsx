import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { ErrorBoundary } from "./components/ErrorBoundary";
import "./App.css";

const rootEl = document.getElementById("root");
if (!rootEl) {
  throw new Error("#root not found");
}

if (!window.gameFactory) {
  rootEl.innerHTML = `
    <div class="boot-error">
      <h1>Preload 未加载</h1>
      <p>Electron preload 脚本失败。请用 <code>start-gui.bat</code> 启动，不要单独运行 electron。</p>
    </div>`;
} else {
  createRoot(rootEl).render(
    <StrictMode>
      <ErrorBoundary>
        <App />
      </ErrorBoundary>
    </StrictMode>,
  );
}
