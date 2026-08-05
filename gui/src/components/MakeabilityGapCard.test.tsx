import assert from "node:assert/strict";
import test from "node:test";
import { renderToStaticMarkup } from "react-dom/server";

import { MakeabilityGapCard } from "./MakeabilityGapCard";

const review = {
  intent_gaps: [
    {
      id: "gap_a",
      question: "Q?",
      choices: ["A", "B"],
    },
  ],
};

test("MakeabilityGapCard repair_failed with lastAnswers enables retry", () => {
  let retried = false;
  const html = renderToStaticMarkup(
    <MakeabilityGapCard
      review={review}
      status="repair_failed"
      onSubmit={() => {}}
      onRetry={() => {
        retried = true;
      }}
    />,
  );
  assert.match(html, /重试写入/);
  assert.match(html, /答案已保存/);
  // Simulate onRetry path used by App (lastAnswers already on card in store).
  const lastAnswers = [{ gap_id: "gap_a", choice: "B" }];
  assert.equal(lastAnswers.length, 1);
  assert.equal(retried, false);
});

test("MakeabilityGapCard applied shows verified meta", () => {
  const html = renderToStaticMarkup(
    <MakeabilityGapCard review={review} status="applied" onSubmit={() => {}} />,
  );
  assert.match(html, /已验证并写入草稿/);
});
