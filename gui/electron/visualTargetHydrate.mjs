/**
 * Catalog scenes in brief.json only store id/title/path.
 * visual_reference lives on scenes/<id>.json after a VT pick.
 */
export function mergeSceneVisualRefsFromShards(scenes, projectRootAbs, io) {
  const join = io.join;
  const existsSync = io.existsSync;
  const readFileSync = io.readFileSync;
  if (!Array.isArray(scenes) || !projectRootAbs) return Array.isArray(scenes) ? scenes : [];
  return scenes.map((row) => {
    if (!row || typeof row !== "object") return row;
    const inline = String(row.visual_reference || "").trim();
    if (inline) return row;
    const shardRel = String(row.path || "").trim().replace(/\\/g, "/");
    if (!shardRel.toLowerCase().endsWith(".json")) return row;
    const abs = join(projectRootAbs, shardRel);
    if (!existsSync(abs)) return row;
    try {
      const body = JSON.parse(readFileSync(abs, "utf-8"));
      const vr = String(body?.visual_reference || "").trim();
      if (!vr) return row;
      return { ...row, visual_reference: vr };
    } catch {
      return row;
    }
  });
}
