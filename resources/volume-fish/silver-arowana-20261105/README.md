> 2026-11-05 历史制作记录退役说明：本批十一鱼已获用户成品接受，旧实验图片、模型、密集数据与候选专用重放链已按授权清理。本页旧路径/命令仅为历史方法记录，不是当前可运行入口或仍存在的图证据。以后从canonical fish.blend修改；当前依赖与保留方法见 `resources/volume-fish/eleven-fish-release-20261105/METHODS.md` 和游戏正式release/history-new-eleven.md。

# Silver arowana adopted authoring — 2026-11-05

70 cm, 1984 triangles / 35 native bones / seven solid fins / two closed original-pixel eyes / two mandibular barbels. Current GLB SHA `c40dd8db8d18db24a9d3b6c8672d8a9bf34bdefb309a8e7f9874a928478f0a71`. No whole-fish user acceptance or installation.

Restore from Foundry resources only, using a new workspace output directory:

```powershell
& E:/blender/blender.exe --background --python resources/scripts/volume-fish/silver_arowana/author_source.py -- E:/game-ai-foundry/resources/volume-fish/silver-arowana-20261105/authoring.profile.json E:/game-ai-foundry/work/silver-arowana-restore
```

`prepared-source.blend` is necessary packed ordinary editable input for adopted body, oral cut, native lip chart, hidden head tissue, pixel eye lenses, paired fins, barbels and native35bone rig/clip. Its three unpaired fin objects deliberately contain empty shells. `authoring.profile.json` recreates their complete finite mesh, per-loop UV/material and normalized four-bone weights, and records all adopted strip/taper/tail/eye/barbel parameters. `cage.profile.json` preserves the full species configuration. This is editable authoring data, not a generic generator or decimated high model. No game experiment module or targetGLB is read by the author.

Actual resource recovery was executed. Every accessor array, embedded PNG byte, material/sampler, node, rig and native animation equals the candidate. Reloaded packed image display names alone differ; recoveredGLB is semantically exact, **not byte-identical**. Ordinary independent cold export from current final fish.blend is byte-identical. Proof is `barbel-root-r24/resource-recovery.validation.json` in the fish's original experiment handoff.

Adopted finite strips split at actual body X rings, preserve original .065 root/.28 blend domains, use <=5nativepixels concave geometry superset with originalRGBA/alpha unchanged, full long-fin root .844925mm tapering to .15. Tail14points align7actual bodycap latitudes; finite same-X/Z width error .398774mm against .4mm. LPfit/heldout final skin weights are explicit profile data. Complete8spoke barbelroot rings retreat .0085native posteriorly, diameter/free3rings exact; actual490 embedding .238–2.008mm. Closed64tri/side eyes preserve44px native fullrim and old8.0505mm actual envelope (new8.0469mm), no cranium expansion.

`adopted-methods.json` records private files/shared dependency SHAs and minimal differences. Shared builders/SOP/checkers were not edited. Source owns nearest9728/MASK.5. Original077body/GPU kernel is unchanged; explicit mixedauxiliaries never masquerade asrigid. Self rules reference `resources/skills/fish-volume-production/references/fin-shell-self-intersection.md`. Reports keep originalSHA; exact per-part scope transports unaffected evidence.

Local SliverArowana artist model is not biological width evidence. Hidden head tissue is generated support with originaleye/lip/lateralgill protection; original sideart remains authoritative. Dry close crown highlights limit tissue detail, actualwater normalreads. Discrete490 is not continuous-time proof. Current ordinary fish.blend/realGLB/coldGLB and unique sourceart remain in the original handoff.
