export interface SaveActivityTransition {
  active: number;
  savingChangedTo?: boolean;
}

export function transitionSaveActivity(
  current: number,
  delta: 1 | -1,
): SaveActivityTransition {
  const active = Math.max(0, current + delta);
  if (current === 0 && active === 1) return { active, savingChangedTo: true };
  if (current > 0 && active === 0) return { active, savingChangedTo: false };
  return { active };
}
