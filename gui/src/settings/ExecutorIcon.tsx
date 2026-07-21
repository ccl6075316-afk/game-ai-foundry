/** Executor brand marks — inline SVG so Electron theming works (CSS mask is flaky). */

import type { ReactElement, ReactNode, SVGProps } from "react";

export type ExecutorIconId = "pi" | "hermes" | "codex" | "cursor";

const ICON_LABEL: Record<ExecutorIconId, string> = {
  pi: "Pi",
  hermes: "Hermes",
  codex: "Codex",
  cursor: "Cursor",
};

type SvgProps = SVGProps<SVGSVGElement> & { title?: string };

function BaseSvg({
  title,
  children,
  className,
  ...rest
}: SvgProps & { children: ReactNode }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="currentColor"
      className={className ?? "executor-icon"}
      role="img"
      aria-label={title}
      {...rest}
    >
      {title ? <title>{title}</title> : null}
      {children}
    </svg>
  );
}

/** Original π mark for embedded Pi. */
function PiMark({ title = ICON_LABEL.pi, ...rest }: SvgProps) {
  return (
    <BaseSvg title={title} {...rest}>
      <path d="M5.5 6.25h13a.75.75 0 0 1 0 1.5h-2.1v9.5a.75.75 0 0 1-1.5 0v-9.5H10.9v8.7c0 1.55-.86 2.55-2.35 2.55-.7 0-1.35-.2-1.85-.55a.75.75 0 1 1 .85-1.24c.25.17.55.29.95.29.7 0 .9-.45.9-1.05v-8.7H5.5a.75.75 0 0 1 0-1.5Z" />
    </BaseSvg>
  );
}

/** Simple Icons — Cursor (CC0). */
function CursorMark({ title = ICON_LABEL.cursor, ...rest }: SvgProps) {
  return (
    <BaseSvg title={title} {...rest}>
      <path d="M11.503.131 1.891 5.678a.84.84 0 0 0-.42.726v11.188c0 .3.162.575.42.724l9.609 5.55a1 1 0 0 0 .998 0l9.61-5.55a.84.84 0 0 0 .42-.724V6.404a.84.84 0 0 0-.42-.726L12.497.131a1.01 1.01 0 0 0-.996 0M2.657 6.338h18.55c.263 0 .43.287.297.515L12.23 22.918c-.062.107-.229.064-.229-.06V12.335a.59.59 0 0 0-.295-.51l-9.11-5.257c-.109-.063-.064-.23.061-.23" />
    </BaseSvg>
  );
}

/** Simple Icons — OpenAI (CC0), used as Codex mark. */
function CodexMark({ title = ICON_LABEL.codex, ...rest }: SvgProps) {
  return (
    <BaseSvg title={title} {...rest}>
      <path d="M22.2819 9.8211a5.9847 5.9847 0 0 0-.5157-4.9108 6.0462 6.0462 0 0 0-6.5098-2.9A6.0651 6.0651 0 0 0 4.9807 4.1818a5.9847 5.9847 0 0 0-3.9977 2.9 6.0462 6.0462 0 0 0 .7427 7.0966 5.98 5.98 0 0 0 .511 4.9107 6.051 6.051 0 0 0 6.5146 2.9001A5.9847 5.9847 0 0 0 13.2599 24a6.0557 6.0557 0 0 0 5.7718-4.2058 5.9894 5.9894 0 0 0 3.9977-2.9001 6.0557 6.0557 0 0 0-.7475-7.0729zm-9.022 12.6081a4.4755 4.4755 0 0 1-2.8764-1.0408l.1419-.0804 4.7783-2.7582a.7948.7948 0 0 0 .3927-.6813v-6.7369l2.02 1.1686a.071.071 0 0 1 .038.052v5.5826a4.504 4.504 0 0 1-4.4945 4.4944zm-9.6607-4.1254a4.4708 4.4708 0 0 1-.5346-3.0137l.142.0852 4.783 2.7582a.7712.7712 0 0 0 .7806 0l5.8428-3.3685v2.3324a.0804.0804 0 0 1-.0332.0615L9.74 19.9502a4.4992 4.4992 0 0 1-6.1408-1.6464zM2.3408 7.8956a4.485 4.485 0 0 1 2.3655-1.9728V11.6a.7664.7664 0 0 0 .3879.6765l5.8144 3.3543-2.0201 1.1685a.0757.0757 0 0 1-.071 0l-4.8303-2.7865A4.504 4.504 0 0 1 2.3408 7.872zm16.5963 3.8558L13.1038 8.364 15.1192 7.2a.0757.0757 0 0 1 .071 0l4.8303 2.7913a4.4944 4.4944 0 0 1-.6765 8.1042v-5.6772a.79.79 0 0 0-.407-.667zm2.0107-3.0231l-.142-.0852-4.7735-2.7818a.7759.7759 0 0 0-.7854 0L9.409 9.2297V6.8974a.0662.0662 0 0 1 .0284-.0615l4.8303-2.7866a4.4992 4.4992 0 0 1 6.6802 4.66zM8.3065 12.863l-2.02-1.1638a.0804.0804 0 0 1-.038-.0567V6.0742a4.4992 4.4992 0 0 1 7.3757-3.4537l-.142.0805L8.704 5.459a.7948.7948 0 0 0-.3927.6813zm1.0976-2.3654l2.602-1.4998 2.6069 1.4998v2.9994l-2.5974 1.4997-2.6067-1.4997Z" />
    </BaseSvg>
  );
}

/**
 * Simplified Nous / Hermes mark (silhouette head+shoulders).
 * Full LobeHub asset is too heavy for a 14px badge; this reads at small size.
 */
function HermesMark({ title = ICON_LABEL.hermes, ...rest }: SvgProps) {
  return (
    <BaseSvg title={title} {...rest}>
      <path d="M12 2.2c-2.1 0-3.8 1.55-3.8 3.55 0 1.35.7 2.45 1.75 3.1-.95.35-1.8.95-2.45 1.75C6.4 11.9 5.8 13.55 5.8 15.4v1.1c0 .55.45 1 1 1h10.4c.55 0 1-.45 1-1v-1.1c0-1.85-.6-3.5-1.7-4.8-.65-.8-1.5-1.4-2.45-1.75 1.05-.65 1.75-1.75 1.75-3.1C15.8 3.75 14.1 2.2 12 2.2zm0 1.6c1.25 0 2.2.9 2.2 1.95S13.25 7.7 12 7.7 9.8 6.8 9.8 5.75 10.75 3.8 12 3.8zM8.05 16.5c.2-1.55.8-2.85 1.7-3.7.7-.65 1.55-1.05 2.25-1.05s1.55.4 2.25 1.05c.9.85 1.5 2.15 1.7 3.7H8.05z" />
    </BaseSvg>
  );
}

const MARKS: Record<ExecutorIconId, (p: SvgProps) => ReactElement> = {
  pi: PiMark,
  hermes: HermesMark,
  codex: CodexMark,
  cursor: CursorMark,
};

export function ExecutorIcon({
  id,
  className = "executor-icon",
  title,
}: {
  id: ExecutorIconId;
  className?: string;
  title?: string;
}) {
  const Mark = MARKS[id];
  return <Mark className={className} title={title ?? ICON_LABEL[id]} />;
}

export function isExecutorIconId(value: string | undefined): value is ExecutorIconId {
  return value === "pi" || value === "hermes" || value === "codex" || value === "cursor";
}
