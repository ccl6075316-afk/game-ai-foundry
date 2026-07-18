import { useEffect, useState } from "react";
import type { ChatAttachment, MediaPreview } from "../chat/types";
import { toRepoMediaRel } from "../chat/toRepoMediaRel";

interface Props {
  attachments: ChatAttachment[];
}

export function MessageMedia({ attachments }: Props) {
  if (!attachments.length) return null;
  return (
    <div className="message-media">
      {attachments.map((item) => (
        <MediaCard key={item.path} item={item} />
      ))}
    </div>
  );
}

function MediaCard({ item }: { item: ChatAttachment }) {
  const mediaPath = toRepoMediaRel(item.path) || item.path;
  const posterPath = item.posterPath
    ? toRepoMediaRel(item.posterPath) || item.posterPath
    : undefined;
  const [preview, setPreview] = useState<MediaPreview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    setPreview(null);
    if (!window.gameFactory?.getMediaPreview) {
      setError("预览 API 不可用（请重启应用）");
      return;
    }
    void window.gameFactory
      .getMediaPreview(mediaPath, posterPath)
      .then((res) => {
        if (cancelled) return;
        if (!res || !(res.previewUrl || res.posterUrl)) {
          setError(`找不到文件：${mediaPath}`);
          setPreview(null);
          return;
        }
        setPreview(res);
      })
      .catch((e) => {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "预览失败");
          setPreview(null);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [mediaPath, posterPath]);

  const open = () => {
    void window.gameFactory.openMedia(mediaPath).then((res) => {
      if (res && res.ok === false) {
        setError(res.error || "无法打开");
      }
    });
  };

  const label = item.label || preview?.name || mediaPath.split(/[/\\]/).pop() || "媒体";
  const isVideo = item.kind === "video" || preview?.kind === "video";
  const thumbUrl = preview?.posterUrl || preview?.previewUrl;

  return (
    <button type="button" className="media-card" onClick={open} title={`打开 ${mediaPath}`}>
      <div className="media-card__frame">
        {thumbUrl && !error ? (
          <img
            src={thumbUrl}
            alt={label}
            className="media-card__img"
            loading="lazy"
            onError={() => setError("缩略图加载失败")}
          />
        ) : (
          <div className="media-card__placeholder">
            {error ? (
              <>
                <div>{isVideo ? "视频" : "图片"} · 加载失败</div>
                <div className="media-card__err">{error}</div>
              </>
            ) : (
              <div>{isVideo ? "视频加载中…" : "图片加载中…"}</div>
            )}
          </div>
        )}
        {isVideo && thumbUrl && !error && (
          <span className="media-card__badge" aria-hidden>
            <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor">
              <path d="M8 5v14l11-7L8 5z" />
            </svg>
          </span>
        )}
      </div>
      <span className="media-card__label">{label}</span>
      <span className="media-card__hint">
        {error ? mediaPath : isVideo ? "点击用系统播放器打开" : "点击查看"}
      </span>
    </button>
  );
}
