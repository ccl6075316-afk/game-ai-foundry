import { useEffect } from "react";

interface Props {
  /** Preview URL (gamefactory-media:// or blob) */
  url: string;
  title?: string;
  pathHint?: string;
  onClose: () => void;
  /** Optional: open in OS viewer */
  onOpenExternal?: () => void;
}

/** In-app image preview so board/asset thumbs do not leave the list for Photos.exe. */
export function MediaLightbox({
  url,
  title,
  pathHint,
  onClose,
  onOpenExternal,
}: Props) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      className="media-lightbox"
      role="dialog"
      aria-modal="true"
      aria-label={title || "图片预览"}
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="media-lightbox__panel">
        <div className="media-lightbox__bar">
          <button type="button" className="btn btn--ghost" onClick={onClose}>
            ← 返回列表
          </button>
          <span className="media-lightbox__title">{title || "预览"}</span>
          {onOpenExternal && (
            <button type="button" className="btn btn--ghost" onClick={onOpenExternal}>
              系统打开
            </button>
          )}
        </div>
        <div className="media-lightbox__frame">
          <img src={url} alt={title || ""} className="media-lightbox__img" />
        </div>
        {pathHint && <p className="media-lightbox__path mono hint">{pathHint}</p>}
      </div>
    </div>
  );
}
