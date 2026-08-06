import type { MakeabilityAnswerResult, MakeabilityCardState, MakeabilityGapAnswer } from "./types";

/** Pure card status from makeability-answer API payload (GUI must not partial-apply). */
export function resolveMakeabilityCardStatus(
  data: MakeabilityAnswerResult,
): MakeabilityCardState["status"] {
  const repairFailedIds = data.repair_failed_ids ?? [];
  const verifiedIds = data.verified_ids ?? [];
  const remaining = data.remaining_intent_count ?? 0;

  if (data.repair_failed || repairFailedIds.length > 0) {
    return "repair_failed";
  }
  if (data.draft_persisted === false) {
    return "repair_failed";
  }
  if (verifiedIds.length > 0 && remaining === 0 && data.ok) {
    return "applied";
  }
  if (data.ok && verifiedIds.length > 0 && remaining > 0) {
    return "repair_failed";
  }
  if (data.ok && verifiedIds.length > 0) {
    return "applied";
  }
  return "pending";
}

/** Persist answers locally before network/CLI — crash-safe retry via lastAnswers. */
export function makeabilityCardLocalSubmitPatch(
  answers: MakeabilityGapAnswer[],
): Pick<MakeabilityCardState, "status" | "lastAnswers"> {
  return {
    status: "repair_failed",
    lastAnswers: answers,
  };
}

export function makeabilityCardAfterServerPatch(
  data: MakeabilityAnswerResult,
  answers: MakeabilityGapAnswer[],
): Pick<MakeabilityCardState, "status" | "lastAnswers"> {
  return {
    status: resolveMakeabilityCardStatus(data),
    lastAnswers: answers,
  };
}
