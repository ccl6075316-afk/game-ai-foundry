/**
 * Map CLI `brief visual-target status --json` + runCli result → GUI IPC payload.
 * Pure helper so we can unit-test without spinning Electron.
 */

/**
 * @param {{ exitCode?: number, stdout?: string, stderr?: string }} cliResult
 *   Shape from runCli — has exitCode, NOT `ok`.
 * @param {(text: string) => any} parseJson
 * @param {{ sceneId?: string | null, looksLikeImagePath?: (s: string) => boolean }} [opts]
 */
export function mapVisualTargetStatusFromCli(cliResult, parseJson, opts = {}) {
  const sid = String(opts.sceneId || "").trim() || null;
  const looksLikeImagePath =
    opts.looksLikeImagePath ||
    ((ref) => {
      const s = String(ref || "").trim().replace(/\\/g, "/");
      if (!s || s.length > 400 || s.includes("://")) return false;
      return /\.(png|jpe?g|webp|gif)$/i.test(s);
    });

  const data = parseJson(cliResult?.stdout || "");
  // CRITICAL: runCli returns { exitCode, stdout, stderr } — never `ok`.
  // Checking `!cliResult.ok` always fails and forces ready=false.
  if ((cliResult?.exitCode ?? 1) !== 0 || !data || data.ok === false) {
    return {
      ok: false,
      ready: false,
      visual_reference: "",
      candidates: [],
      scenes: [],
      error:
        (typeof data?.error === "string" && data.error) ||
        cliResult?.stderr ||
        "visual-target status failed",
    };
  }

  const globalRef = String(data.visual_reference || "").trim();
  const globalReady = Boolean(data.global_ready);
  return {
    ok: true,
    ready: Boolean(data.ready),
    disk_marked: Boolean(data.disk_marked),
    global_ready: globalReady,
    global_selected_id: data.global_selected_id ?? null,
    global_has_selected_image: Boolean(data.global_has_selected_image),
    global_preview_path:
      data.global_preview_path ?? (globalReady && globalRef ? globalRef : null),
    visual_reference: globalRef,
    path_shaped: looksLikeImagePath(globalRef),
    file_ok: globalReady,
    selected_id: data.selected_id ?? null,
    scene_id: sid,
    scenes: (Array.isArray(data.scenes) ? data.scenes : []).map((s) => ({
      id: String(s.id || "").trim(),
      title: String(s.title || s.id || "").trim(),
      visual_reference: String(s.visual_reference || "").trim(),
      ready: Boolean(s.ready),
      selected_id: s.selected_id ? String(s.selected_id).trim().toLowerCase() : null,
      has_selected_image: Boolean(s.has_selected_image),
      marked: Boolean(s.marked),
      preview_path:
        s.preview_path ||
        (s.ready && s.visual_reference ? String(s.visual_reference).trim() : null),
    })),
    candidates: [],
  };
}
