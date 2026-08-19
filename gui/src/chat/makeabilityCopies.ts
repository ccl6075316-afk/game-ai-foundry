/** Assistant copy for Makeability Critic cards (avoid duplicating the review summary). */

export function makeabilityCardCopies(
  head: string,
  hasIntent: boolean,
  hasRepair: boolean,
): { repairContent?: string; intentContent?: string } {
  const summary = head.trim() || "制作审查完成。";
  if (hasRepair && hasIntent) {
    return {
      repairContent: `${summary}\n\n先处理下方「重试写入」卡片，再回答新的意图缺口。`,
      intentContent: "请在新卡片中点选选项并「写入草稿」。",
    };
  }
  if (hasRepair) {
    return {
      repairContent: `${summary}\n\n下方卡片可「重试写入」已保存的答案（无需重新选题）。`,
    };
  }
  if (hasIntent) {
    return {
      intentContent: `${summary}\n\n下方 **制作审查 · Critic** 卡片中点选选项并「写入草稿」。`,
    };
  }
  return {};
}
