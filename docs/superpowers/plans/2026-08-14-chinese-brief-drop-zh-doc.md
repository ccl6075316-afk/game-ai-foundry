# Chinese Brief + Drop brief.zh.md Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make brief/shard narrative Chinese-first, remove the `brief.zh.md` companion pipeline, require prompt-crafter to secondary-generate English prompts, and one-shot localize fishing narrative fields.

**Architecture:** Skills + host copy flip to Chinese narrative; delete zh-doc write paths (CLI/GUI/IT/persist); add a small CJK guard in `assemble_asset_prompt` / visual-target assemble so Chinese brief text cannot become the final English prompt without craft; add `brief localize` for one-shot EN→ZH rewrite of narrative fields into shards.

**Tech Stack:** Python 3.11+, existing unittest/Click, Electron/React GUI, prompt-crafter skills under `resources/skills/`.

**Spec:** [`docs/superpowers/specs/2026-08-14-chinese-brief-drop-zh-doc-design.md`](../specs/2026-08-14-chinese-brief-drop-zh-doc-design.md)

## Global Constraints

- Narrative fields Chinese-first; `id` / paths / technical enums stay English slug / English values.
- No validate hard-fail on language (English leftovers allowed).
- LLM craft on → structured fields must be English; do not paste Chinese `description` into final prompt.
- LLM craft off + CJK in injected subject → warn and refuse assemble (chosen default).
- Remove `brief.zh.md` generation; no replacement Chinese export md.
- One-shot localize for current project(s); not a full-repo scanner.
- Frequent commits; do not push unless user asks.

## File map

| File | Responsibility |
|------|----------------|
| `resources/skills/orchestrator/{brief-brainstorm,commit-brief,host-chat,brief-enrich}.md` | Chinese-first narrative rules |
| `resources/skills/prompt-crafter/{asset-planner,visual-target,shared-locks}.md` | Secondary English generation discipline |
| `resources/skills/it/diagnose.md` | Drop zh-doc ops |
| `cli/host_chat.py` | Stop persist-time zh write |
| `cli/brief_cmds.py` | Remove zh-doc commands / export zh; add `brief localize` |
| `cli/brief_zh_doc.py` + `cli/test_brief_zh_doc.py` | Delete |
| `cli/pi_foundry_tools.py` + `cli/test_pi_foundry_tools.py` | Drop zh-doc from profiles |
| `cli/prompt_craft.py` + new/extend tests | CJK assemble guard |
| `cli/brief_localize.py` (new) + tests | Narrative EN→ZH rewrite helper |
| `gui/src/{App.tsx,components/DocsPreviewPanel.tsx,chat/roles.ts,vite-env.d.ts}` | Remove zh-doc UI |
| `gui/electron/main.mjs` | Drop zh-doc IPC if any |
| `docs/{README.md,AI-HANDOFF.md}` | Language policy + no zh companion |
| fishing project shards | One-shot localize + delete `brief.zh.md` |

---

### Task 1: Skills + docs — Chinese-first narrative

**Files:**
- Modify: `resources/skills/orchestrator/brief-brainstorm.md`
- Modify: `resources/skills/orchestrator/commit-brief.md`
- Modify: `resources/skills/orchestrator/host-chat.md`
- Modify: `resources/skills/orchestrator/brief-enrich.md`
- Modify: `docs/AI-HANDOFF.md` (brief field language notes)
- Modify: `docs/README.md` (drop `brief.zh.md` bullet)

**Interfaces:**
- Consumes: spec language table
- Produces: skill text that agents read on next chat turn

- [ ] **Step 1: Replace English-narrative rules**

In each orchestrator skill above, replace lines like「brief 内 description / art_direction 用英文」with:

```markdown
- brief / 分册叙事字段（`description` / `art_direction` / `gameplay_loop` / `session_goal` / `summary` / `notes` / 资产外观描述等）**中文优先**。
- `id` 仍为英文 slug；技术枚举（`type` / `content_class` / `view` 等）保持英文取值。
- 对用户说话用中文。生图英文 prompt 由 **prompt-crafter 二次生成**，不要把 brief 当最终 prompt。
```

Remove any「便于后续 prompt-crafter 所以写英文」rationale.

- [ ] **Step 2: Docs**

In `docs/README.md` Brief bullet: remove「导出前可 brief.zh.md」; say 文档栏预览中文分册.

In `docs/AI-HANDOFF.md` field table: mark narrative fields 中文优先; note `brief.zh.md` removed.

- [ ] **Step 3: Commit**

```bash
git add resources/skills/orchestrator/brief-brainstorm.md resources/skills/orchestrator/commit-brief.md resources/skills/orchestrator/host-chat.md resources/skills/orchestrator/brief-enrich.md docs/AI-HANDOFF.md docs/README.md
git commit -m "docs: Chinese-first brief narrative in skills and handoff"
```

---

### Task 2: Stop host persist from writing brief.zh.md

**Files:**
- Modify: `cli/host_chat.py` (~465–471)
- Modify: `cli/test_host_chat.py` (persist/zh assertions ~4215)

**Interfaces:**
- Consumes: `_persist_working_draft` / equivalent persist helper
- Produces: persist writes only draft JSON

- [ ] **Step 1: Write failing test expectation**

Find the test that asserts `brief.zh.md` exists after persist. Change it to assert the file is **not** created:

```python
zh = proj / "brief.zh.md"
self.assertFalse(zh.is_file(), "persist must not write brief.zh.md")
```

- [ ] **Step 2: Run test — expect FAIL** (still writes zh)

```bash
cd cli && python -m unittest test_host_chat -q
```

- [ ] **Step 3: Remove zh write block**

Delete from persist path:

```python
# Keep Chinese companion in sync with the machine draft (no LLM on every save).
try:
    from brief_zh_doc import write_brief_zh_document
    write_brief_zh_document(brief_path, out, config={}, use_llm=False)
except Exception:
    pass
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
cd cli && python -m unittest test_host_chat -q
```

- [ ] **Step 5: Commit**

```bash
git add cli/host_chat.py cli/test_host_chat.py
git commit -m "fix: stop host persist from writing brief.zh.md"
```

---

### Task 3: Remove CLI zh-doc + export companion

**Files:**
- Modify: `cli/brief_cmds.py` (`chat zh-doc`, `brief zh-doc`, export `--skip-zh-doc` and write calls)
- Modify: any export tests referencing `zh_doc_*`
- Delete later in Task 5: module itself (this task only stops CLI surface)

**Interfaces:**
- Produces: no Click commands named `zh-doc`; export JSON has no `zh_doc_path`

- [ ] **Step 1: Failing/update tests**

If tests call `brief chat zh-doc` or assert export `zh_doc_path`, update to expect command missing or field absent.

- [ ] **Step 2: Remove commands and export hooks**

- Delete `@chat_group.command("zh-doc")` and `@brief_group.command("zh-doc")` handlers.
- On export: remove `--skip-zh-doc`, remove `write_brief_zh_document` call and echoed paths.
- Grep `zh_doc` / `brief_zh_doc` in `brief_cmds.py` until clean.

- [ ] **Step 3: Smoke**

```bash
cd cli && python gamefactory.py brief --help
python gamefactory.py brief chat --help
```

Expected: no `zh-doc` subcommand.

- [ ] **Step 4: Commit**

```bash
git add cli/brief_cmds.py cli/test_*.py
git commit -m "feat: remove brief zh-doc CLI and export companion write"
```

---

### Task 4: Drop zh-doc from Pi/IT tool profiles + GUI

**Files:**
- Modify: `cli/pi_foundry_tools.py`
- Modify: `cli/test_pi_foundry_tools.py`
- Modify: `resources/skills/it/diagnose.md`
- Modify: `gui/src/chat/roles.ts`
- Modify: `gui/src/components/DocsPreviewPanel.tsx`
- Modify: `gui/src/App.tsx`
- Modify: `gui/src/vite-env.d.ts` (optional: leave types or remove `zh_doc_*`)
- Modify: `gui/electron/main.mjs` if it special-cases zh-doc

**Interfaces:**
- Produces: no IT shortcut / Docs button / whitelist tuple for zh-doc

- [ ] **Step 1: Update Pi whitelist tests**

Remove expectations that `("brief", "zh-doc")` or `("brief", "chat", "zh-doc")` appear in brief/IT profiles. Assert they are absent.

- [ ] **Step 2: Edit `pi_foundry_tools.py` + `diagnose.md`**

Remove zh-doc from allowlists, help text, example argv blocks, and IT diagnose table rows.

- [ ] **Step 3: GUI**

- `roles.ts`: remove IT quick action「生成中文说明」.
- `DocsPreviewPanel.tsx`: remove「生成中文说明」button and `onZhDoc` props if only used for that.
- `App.tsx`: remove `runZhDoc` / choice handlers / assistant strings about 生成中文说明; remove post-export focus on `brief.zh.md`.
- Clean `vite-env.d.ts` / `main.mjs` zh_doc fields only if they become unused (no dangling required props).

- [ ] **Step 4: Run**

```bash
cd cli && python -m unittest test_pi_foundry_tools -q
```

- [ ] **Step 5: Commit**

```bash
git add cli/pi_foundry_tools.py cli/test_pi_foundry_tools.py resources/skills/it/diagnose.md gui/src/chat/roles.ts gui/src/components/DocsPreviewPanel.tsx gui/src/App.tsx gui/src/vite-env.d.ts gui/electron/main.mjs
git commit -m "feat: remove zh-doc from IT whitelist and GUI entry points"
```

---

### Task 5: Delete brief_zh_doc module

**Files:**
- Delete: `cli/brief_zh_doc.py`
- Delete: `cli/test_brief_zh_doc.py`
- Modify: any remaining imports (`cli/ui_wireframe.py` only imports `BRIEF_DRAFT_NAME` / load helpers — move those constants if needed)

**Interfaces:**
- If `ui_wireframe.py` imports `BRIEF_DRAFT_NAME` from `brief_zh_doc`, move `BRIEF_DRAFT_NAME = "brief.draft.json"` to `brief_shards.py` or a tiny `brief_paths.py` and update imports **before** deleting the module.

- [ ] **Step 1: Relocate shared constants**

```python
# e.g. in brief_shards.py or brief_cmds helpers
BRIEF_DRAFT_NAME = "brief.draft.json"
```

Update `ui_wireframe.py` (and any other) imports.

- [ ] **Step 2: Grep clean**

```bash
rg "brief_zh_doc|BRIEF_ZH_DOC|write_brief_zh|zh-doc" cli gui resources/skills docs/AI-HANDOFF.md docs/README.md
```

Expected: only historical RELEASE notes / archived reviews (leave those).

- [ ] **Step 3: Delete module + tests; run suite subset**

```bash
cd cli && python -m unittest test_host_chat test_pi_foundry_tools test_brief_shards -q
```

- [ ] **Step 4: Commit**

```bash
git add -A cli/brief_zh_doc.py cli/test_brief_zh_doc.py cli/ui_wireframe.py cli/brief_shards.py
git commit -m "chore: delete brief_zh_doc module and tests"
```

---

### Task 6: prompt-crafter — secondary English + CJK assemble guard

**Files:**
- Modify: `resources/skills/prompt-crafter/asset-planner.md`
- Modify: `resources/skills/prompt-crafter/visual-target.md`
- Modify: `cli/prompt_craft.py`
- Create or modify: `cli/test_prompt_craft.py` (create if missing)

**Interfaces:**
- Produces: `contains_cjk(text: str) -> bool`; assemble raises `PromptCraftError` if injecting CJK subject/style without English fields

- [ ] **Step 1: Failing tests**

```python
# cli/test_prompt_craft.py
import unittest
from prompt_craft import PromptCraftError, assemble_asset_prompt, contains_cjk

class CjkAssembleGuardTests(unittest.TestCase):
    def test_contains_cjk(self):
        self.assertTrue(contains_cjk("红色小船"))
        self.assertFalse(contains_cjk("red boat"))

    def test_assemble_rejects_cjk_description_fallback(self):
        project = {"view": "side", "art_direction": "像素风"}
        spec = {"description": "码头上的红色小船", "type": "character"}
        with self.assertRaises(PromptCraftError):
            assemble_asset_prompt({}, project=project, spec=spec)

    def test_assemble_accepts_english_subject(self):
        project = {"view": "side"}
        spec = {"description": "码头上的红色小船", "type": "character"}
        prompt = assemble_asset_prompt(
            {"subject": "A small red boat at a wooden pier"},
            project=project,
            spec=spec,
        )
        self.assertIn("red boat", prompt.lower())
```

- [ ] **Step 2: Run — expect FAIL** (`contains_cjk` missing / no raise)

```bash
cd cli && python -m unittest test_prompt_craft.CjkAssembleGuardTests -q
```

- [ ] **Step 3: Implement**

```python
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")

def contains_cjk(text: str) -> bool:
    return bool(_CJK_RE.search(text or ""))
```

In `assemble_asset_prompt`, after description→subject fallback (and similarly if `style_lock` falls back from Chinese `art_direction`), if `contains_cjk(cleaned.get("subject",""))` or CJK in critical assembled fields that came from brief fallback:

```python
raise PromptCraftError(
    "Chinese brief text cannot be used as the final image prompt; "
    "re-run prompt craft with LLM to secondary-generate English fields"
)
```

Do **not** block when LLM already supplied English `subject`.

Mirror the same guard for visual-target assemble fallback paths that inject Chinese prose.

- [ ] **Step 4: Skills**

In `asset-planner.md` / `visual-target.md` add:

```markdown
Brief narrative may be Chinese. You MUST secondary-generate English structured fields.
Never copy Chinese description/art_direction verbatim into subject/style_lock/scene/hero.
```

- [ ] **Step 5: Tests PASS + commit**

```bash
cd cli && python -m unittest test_prompt_craft.CjkAssembleGuardTests -q
git add cli/prompt_craft.py cli/test_prompt_craft.py resources/skills/prompt-crafter/asset-planner.md resources/skills/prompt-crafter/visual-target.md
git commit -m "feat: block CJK brief text from final assembled image prompts"
```

---

### Task 7: `brief localize` + fishing one-shot

**Files:**
- Create: `cli/brief_localize.py`
- Create: `cli/test_brief_localize.py`
- Modify: `cli/brief_cmds.py` (`brief localize`)
- Modify: fishing project under `projects/fishing-2d` **or** external `e:\game-ai-foundry\projects\fishing-2d` (separate git) — narrative shards + delete `brief.zh.md`

**Interfaces:**
- Produces:

```python
def localize_brief_narratives(
    brief_path: Path,
    *,
    translator: Callable[[str, str], str],
    i_confirm: bool,
) -> dict[str, Any]:
    """Rewrite narrative fields to Chinese via translator(field_name, text)->text.
    Returns {ok, changed_paths, skipped}."""
```

`translator` in production wraps host LLM; tests inject identity/map.

Narrative keys (non-exhaustive but required set):  
`description`, `art_direction`, `gameplay_loop`, `session_goal`, `summary`, `notes`, `usage_description`  
Plus asset `name` **only if** it is English prose the user wants Chinese — **default: do not change `name`/`title` if already CJK; translate English titles/summaries**. Never change `id`/`path`/`type`/`content_class`.

- [ ] **Step 1: Unit test with fake translator**

```python
def test_localize_rewrites_shard_description(self):
    # write catalog scene with English summary
    # translator: lambda key, text: "中文" + text
    # localize_brief_narratives(...)
    # reload shard → summary startswith 中文
    # id unchanged
```

- [ ] **Step 2: Implement `brief_localize.py` + Click**

```text
brief localize --brief PATH --json --i-confirm
```

Without `--i-confirm` → exit 2. Walk catalog refs, load shards, rewrite narrative keys, `save_json_shard`, rewrite thin brief project intro fields if present.

- [ ] **Step 3: Run fishing localize** (real LLM or approved batch)

```bash
cd cli && python gamefactory.py brief localize --brief ../projects/fishing-2d/brief.json --i-confirm --json
```

If fishing is the external repo at `projects/fishing-2d`, commit there separately: narrative JSON + delete `brief.zh.md`.

- [ ] **Step 4: Commit Foundry CLI**

```bash
git add cli/brief_localize.py cli/test_brief_localize.py cli/brief_cmds.py
git commit -m "feat: add brief localize for one-shot Chinese narrative migration"
```

- [ ] **Step 5: Commit fishing** (if user wants; separate repo)

```bash
cd projects/fishing-2d && git add -A && git commit -m "chore: localize brief narratives to Chinese; drop brief.zh.md"
```

---

### Task 8: Integration smoke + UNRELEASED note

**Files:**
- Modify: `docs/RELEASE-NOTES-UNRELEASED.md`

- [ ] **Step 1: Grep product paths**

```bash
rg "brief\\.zh|zh-doc|生成中文说明" cli gui/src resources/skills docs/AI-HANDOFF.md docs/README.md
```

Expected: clean (except this plan/spec and historical RELEASE-NOTES-0.x).

- [ ] **Step 2: Run focused tests**

```bash
cd cli && python -m unittest test_host_chat test_pi_foundry_tools test_brief_shards test_brief_localize test_prompt_craft -q
```

- [ ] **Step 3: UNRELEASED bullet**

```markdown
- Brief 叙事中文优先；移除 `brief.zh.md`；prompt-crafter 二次生成英文 prompt；`brief localize` 一次迁移
```

- [ ] **Step 4: Commit**

```bash
git add docs/RELEASE-NOTES-UNRELEASED.md
git commit -m "docs: note Chinese brief and zh-doc removal in UNRELEASED"
```

---

## Self-review (plan vs spec)

| Spec requirement | Task |
|------------------|------|
| Chinese-first narrative | T1 |
| Delete zh pipeline CLI/GUI/IT/persist | T2–T5 |
| Docs drop zh | T1, T8 |
| prompt-crafter secondary English + no CJK final prompt | T6 |
| One-shot localize fishing | T7 |
| No language validate hard-fail | (no task adds validate — intentional) |
| LLM-off fallback = refuse CJK inject | T6 |

No TBD placeholders. `BRIEF_DRAFT_NAME` relocation called out before module delete.

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-14-chinese-brief-drop-zh-doc.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — this session with executing-plans checkpoints  

Which approach?
