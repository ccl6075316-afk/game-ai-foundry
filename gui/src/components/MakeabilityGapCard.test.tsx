import assert from "node:assert/strict";
import test from "node:test";
import { act } from "react";
import { createRoot } from "react-dom/client";
import { Window } from "happy-dom";
import { renderToStaticMarkup } from "react-dom/server";

import { MakeabilityGapCard } from "./MakeabilityGapCard";
import { makeabilityCardLocalSubmitPatch } from "../chat/makeabilityCardStatus";

const review = {
  intent_gaps: [
    {
      id: "gap_a",
      question: "Q?",
      choices: ["A", "B"],
    },
  ],
};

test("MakeabilityGapCard repair_failed renders retry affordance", () => {
  const html = renderToStaticMarkup(
    <MakeabilityGapCard review={review} status="repair_failed" onSubmit={() => {}} onRetry={() => {}} />,
  );
  assert.match(html, /重试写入/);
  assert.match(html, /答案已保存/);
});

test("MakeabilityGapCard retry click invokes onRetry (lastAnswers resubmit path)", async () => {
  const window = new Window({ url: "https://localhost/" });
  const { document } = window;
  (globalThis as { window?: Window; document?: Document }).window = window as unknown as Window;
  (globalThis as { document?: Document }).document = document as unknown as Document;

  let retried = false;
  const lastAnswers = [{ gap_id: "gap_a", choice: "B" }];
  const localPatch = makeabilityCardLocalSubmitPatch(lastAnswers);
  assert.equal(localPatch.status, "repair_failed");
  assert.deepEqual(localPatch.lastAnswers, lastAnswers);

  const host = document.createElement("div");
  document.body.appendChild(host);
  const root = createRoot(host as unknown as Element);

  await act(async () => {
    root.render(
      <MakeabilityGapCard
        review={review}
        status="repair_failed"
        onSubmit={() => {}}
        onRetry={() => {
          // App wires: lastAnswers from card store → handleMakeabilityAnswer
          retried = true;
          assert.deepEqual(localPatch.lastAnswers, lastAnswers);
        }}
      />,
    );
  });

  const button = host.querySelector("button.makeability-gap-card__submit") as HTMLButtonElement | null;
  assert.ok(button, "retry button missing");
  assert.match(button.textContent || "", /重试写入/);

  await act(async () => {
    button.click();
  });
  assert.equal(retried, true);

  await act(async () => {
    root.unmount();
  });
  host.remove();
});

test("MakeabilityGapCard applied shows verified meta", () => {
  const html = renderToStaticMarkup(
    <MakeabilityGapCard review={review} status="applied" onSubmit={() => {}} />,
  );
  assert.match(html, /已验证并写入草稿/);
});
