import { useEffect, useState } from "react";
import type { VtGlobalMark, VtSceneMark } from "../chat/vtProgressFormat";
import { vtIsMarked, vtMarkBadge } from "../chat/vtProgressFormat";
import { toRepoMediaRel } from "../chat/toRepoMediaRel";
import { catalogDisplayTitle } from "./briefPreviewFormat";
import { MediaLightbox } from "./MediaLightbox";

export type VtBoardItem = VtSceneMark & { preview_path?: string | null };

interface Props {
  globalMark: VtGlobalMark & { preview_path?: string | null };
  scenes: VtBoardItem[];
  onRefresh?: () => void;
  onFocusScene?: (sceneId: string, title: string) => void | Promise<void>;
}

type LightboxState = {
  url: string;
  title: string;
  path: string;
};

function VtThumb({
  label,
  badge,
  path,
  emptyHint,
  onOpen,
  onPin,
}: {
  label: string;
  badge: string;
  path?: string | null;
  emptyHint: string;
  onOpen: (payload: LightboxState) => void;
  onPin?: () => void | Promise<void>;
}) {
  const mediaPath = path ? toRepoMediaRel(path) || path : "";
  const [url, setUrl] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setUrl(null);
    setErr(null);
    if (!mediaPath || !window.gameFactory?.getMediaPreview) return;
    void window.gameFactory
      .getMediaPreview(mediaPath)
      .then((res) => {
        if (cancelled) return;
        if (!res?.previewUrl) {
          setErr("无图");
          return;
        }
        setUrl(res.previewUrl);
      })
      .catch(() => {
        if (!cancelled) setErr("加载失败");
      });
    return () => {
      cancelled = true;
    };
  }, [mediaPath]);

  return (
    <button
      type="button"
      className={"vt-board-card" + (mediaPath ? "" : " vt-board-card--empty")}
      onClick={() => {
        void (async () => {
          await onPin?.();
          if (!mediaPath || !url) return;
          onOpen({ url, title: label, path: mediaPath });
        })();
      }}
      title={mediaPath || emptyHint}
    >
      <div className="vt-board-card__frame">
        {url && !err ? (
          <img src={url} alt={label} className="vt-board-card__img" loading="lazy" />
        ) : (
          <span className="vt-board-card__placeholder">{err || emptyHint}</span>
        )}
        <span className="vt-board-card__badge">{badge}</span>
      </div>
      <span className="vt-board-card__label">{label}</span>
    </button>
  );
}

/** Compact north-star strip for the pipeline board. */
export function BoardVtStrip({ globalMark, scenes, onRefresh, onFocusScene }: Props) {
  const [lightbox, setLightbox] = useState<LightboxState | null>(null);
  const marked = scenes.filter((s) => vtIsMarked(s) || Boolean(s.preview_path));
  const hasAny =
    Boolean(globalMark.preview_path) ||
    vtIsMarked(globalMark) ||
    marked.length > 0 ||
    scenes.some((s) => Boolean(s.preview_path));

  return (
    <section className="vt-board-strip" aria-label="北极星选定">
      <div className="vt-board-strip__head">
        <h3>北极星</h3>
        <span className="vt-board-strip__meta">
          {scenes.length
            ? `${marked.length}/${scenes.length} 场景已选`
            : vtIsMarked(globalMark) || globalMark.preview_path
              ? "全局已选"
              : "尚未选定"}
        </span>
        {onRefresh && (
          <button type="button" className="btn btn--ghost vt-board-strip__refresh" onClick={onRefresh}>
            刷新图
          </button>
        )}
      </div>
      {!hasAny ? (
        <p className="vt-board-strip__empty hint">
          尚无选定图。在策划对话里生成并「选用北极星」后，缩略图会出现在这里。
        </p>
      ) : (
        <div className="vt-board-strip__row">
          <VtThumb
            label="全局"
            badge={vtMarkBadge(globalMark)}
            path={globalMark.preview_path}
            emptyHint="未选"
            onOpen={setLightbox}
          />
          {scenes.map((s) => {
            const label = catalogDisplayTitle(s);
            return (
            <VtThumb
              key={s.id}
              label={label}
              badge={vtMarkBadge(s)}
              path={s.preview_path || s.visual_reference}
              emptyHint="○"
              onOpen={setLightbox}
              onPin={
                onFocusScene
                  ? () => onFocusScene(s.id, label)
                  : undefined
              }
            />
            );
          })}
        </div>
      )}
      {lightbox && (
        <MediaLightbox
          url={lightbox.url}
          title={lightbox.title}
          pathHint={lightbox.path}
          onClose={() => setLightbox(null)}
          onOpenExternal={() => {
            void window.gameFactory?.openMedia?.(lightbox.path);
          }}
        />
      )}
    </section>
  );
}
