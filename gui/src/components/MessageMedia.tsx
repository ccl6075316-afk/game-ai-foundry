import { useEffect, useState } from "react";
import type { ChatAttachment, MediaPreview } from "../chat/types";

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
  const [preview, setPreview] = useState<MediaPreview | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void window.gameFactory
      .getMediaPreview(item.path, item.posterPath)
      .then((res) => {
        if (!cancelled) setPreview(res);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });
    return () => {
      cancelled = true;
    };
  }, [item.path, item.posterPath]);

  const open = () => {
    void window.gameFactory.openMedia(item.path);
  };

  const label = item.label || preview?.name || item.path.split(/[/\\]/).pop() || "媒体";
  const isVideo = item.kind === "video" || preview?.kind === "video";
  const thumbUrl = preview?.posterUrl || preview?.previewUrl;

  return (
    <button type="button" className="media-card" onClick={open} title={`打开 ${label}`}>
      <div className="media-card__frame">
        {thumbUrl && !error ? (
          <img src={thumbUrl} alt={label} className="media-card__img" loading="lazy" />
        ) : (
          <div className="media-card__placeholder">
            {isVideo ? "视频" : "图片"}
          </div>
        )}
        {isVideo && (
          <span className="media-card__badge" aria-hidden>
            <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor">
              <path d="M8 5v14l11-7L8 5z" />
            </svg>
          </span>
        )}
      </div>
      <span className="media-card__label">{label}</span>
      <span className="media-card__hint">{isVideo ? "点击用系统播放器打开" : "点击查看"}</span>
    </button>
  );
}
