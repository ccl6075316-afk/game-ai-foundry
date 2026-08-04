import { useMemo, useState } from "react";
import type { MakeabilityIntentGap, MakeabilityReview } from "../chat/types";

export interface MakeabilityGapAnswer {
  gap_id: string;
  choice?: string;
  note?: string;
}

interface Props {
  review: MakeabilityReview;
  status?: "pending" | "applied" | "dismissed";
  busy?: boolean;
  onSubmit: (answers: MakeabilityGapAnswer[]) => void;
}

export function MakeabilityGapCard({
  review,
  status = "pending",
  busy = false,
  onSubmit,
}: Props) {
  const gaps = useMemo(
    () =>
      (review.intent_gaps || []).filter(
        (g): g is MakeabilityIntentGap & { id: string } =>
          Boolean(g && String(g.id || "").trim()),
      ),
    [review.intent_gaps],
  );

  const [choices, setChoices] = useState<Record<string, string>>({});
  const [notes, setNotes] = useState<Record<string, string>>({});

  if (!gaps.length) return null;

  const pick = (gapId: string, choice: string) => {
    setChoices((prev) => ({ ...prev, [gapId]: choice }));
  };

  const submit = () => {
    const answers: MakeabilityGapAnswer[] = [];
    for (const gap of gaps) {
      const choice = (choices[gap.id] || "").trim();
      const note = (notes[gap.id] || "").trim();
      if (!choice && !note) continue;
      answers.push({
        gap_id: gap.id,
        ...(choice ? { choice } : {}),
        ...(note ? { note } : {}),
      });
    }
    if (!answers.length) return;
    onSubmit(answers);
  };

  const answered = gaps.filter((g) => (choices[g.id] || notes[g.id] || "").trim()).length;
  const locked = status !== "pending" || busy;

  return (
    <div
      className={
        "makeability-gap-card" +
        (status !== "pending" ? " makeability-gap-card--done" : "")
      }
    >
      <div className="makeability-gap-card__head">
        <span className="makeability-gap-card__badge">制作审查 · Critic</span>
        <span className="makeability-gap-card__meta">
          {status === "pending"
            ? `独立子 Agent · ${gaps.length} 条意图缺口`
            : status === "applied"
              ? "已写入草稿"
              : "已关闭"}
        </span>
      </div>
      {status === "pending" ? (
        <>
          <p className="makeability-gap-card__hint">
            点选选项或填写补充后点「写入草稿」——不经主对话 LLM 猜意图。
          </p>
          <div className="makeability-gap-card__gaps">
            {gaps.map((gap) => (
              <div key={gap.id} className="makeability-gap-card__gap">
                <div className="makeability-gap-card__qid">
                  <code>{gap.id}</code>
                </div>
                <div className="makeability-gap-card__q">{gap.question || "（未描述）"}</div>
                {gap.why_blocking ? (
                  <div className="makeability-gap-card__why">{gap.why_blocking}</div>
                ) : null}
                {(gap.choices || []).length > 0 ? (
                  <div className="makeability-gap-card__choices">
                    {(gap.choices || []).map((c) => {
                      const selected = choices[gap.id] === c;
                      return (
                        <button
                          key={c}
                          type="button"
                          className={
                            "makeability-gap-card__choice" +
                            (selected ? " makeability-gap-card__choice--on" : "")
                          }
                          disabled={locked}
                          onClick={() => pick(gap.id, c)}
                        >
                          {c}
                        </button>
                      );
                    })}
                  </div>
                ) : null}
                <input
                  className="makeability-gap-card__note"
                  type="text"
                  disabled={locked}
                  placeholder="其他说明（可选）"
                  value={notes[gap.id] || ""}
                  onChange={(e) =>
                    setNotes((prev) => ({ ...prev, [gap.id]: e.target.value }))
                  }
                />
              </div>
            ))}
          </div>
          <div className="makeability-gap-card__footer">
            <button
              type="button"
              className="makeability-gap-card__submit"
              disabled={locked || answered === 0}
              onClick={submit}
            >
              写入草稿（{answered}/{gaps.length}）
            </button>
          </div>
        </>
      ) : null}
    </div>
  );
}
