# Unreleased — 下一版 Release Notes 草稿

相对当前已打标签的 [`v0.0.8`](RELEASE-NOTES-0.0.8.md)。打版时把本节并入正式 `RELEASE-NOTES-x.y.z.md`。

- **外置工程根**：新建仍默认 `projects/<slug>/`；GUI「打开外置工程…」或 CLI `project external add` 登记独立 Godot 仓（索引 `external-projects.json`）；虚拟键 `external:<id>/brief.json`；双形态 Godot 探测（根或 `game/`）；pipeline / brief 产物写在外置根；从列表移除不删磁盘。
- **Brief 补全 + 议题头脑风暴**：策划侧「补全细节」「议题头脑风暴」按钮（不绑导出）；CLI `brief chat enrich` / `topic-brainstorm` / `brainstorm-apply`；开放式加厚玩家可见信息与参数名，多角色先吵后拣写回 draft，并提议资产候选；具体数值仍可进 production。
