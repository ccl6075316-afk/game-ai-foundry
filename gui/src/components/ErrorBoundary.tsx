import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("GUI render error:", error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="boot-error">
          <h1>界面加载失败</h1>
          <pre>{this.state.error.message}</pre>
          <p className="hint">
            若窗口全黑：请先关闭旧窗口，再运行 start-gui.bat；确保 Vite 在 5173 端口已启动。
          </p>
        </div>
      );
    }
    return this.props.children;
  }
}
