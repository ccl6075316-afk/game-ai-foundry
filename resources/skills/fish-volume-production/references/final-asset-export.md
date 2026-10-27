# 实验结束时的正式资产固化

用户不需要定期提醒导出。执行者每次准备把本轮鱼类工作标为完成、交付或安装为正式资源时，自动执行本节；未解决的实验问题仍留候选，不冒称最后一轮。用户要求只看实验时，可以交实验预览，明确尚未固化，不能写为正式成品。

**本地脚本合并例外**：仅把 Godot 已有静态装配迁入可编辑源/GLB、尚未正式交付时，按[生产SOP第0.2节](production-sop.md#02-本地-godot-静态脚本合并检查点临时)完成本地迁移检查点。仍需真实导出、新进程关闭旧静态构建链冷读、旧实际装配与新导出的网格/UV/权重/材质/代表动作画面对照，并在既有验证报告写清哈希、差异、已知缺陷和延后项。这一阶段暂不重复完整鳍根及整鳍面177/490门，也不补历史逐鱼账本；旧报告因重导出失效时不得沿用通过结论。正式流程的完整鳍专项和 `volume sop-check` 在后续两次鳍大修后冻结正式候选时执行。迁移差异或新增明显穿体须先局部修复；本地检查点不能称正式鱼资产交付。

## 顺序与边界

1. 合并本轮已稳定修改，审阅实际多视/源图/代表性动作。列清身体、眼、嘴、鳍的实际组成和依赖，区分静态几何/UV/权重/纹理与实时动画/行为/环境。进程内缓存命中不算固化。
2. 应属于模型的静态结果回写可编辑 `.blend` 和通用制作工具/物种参数，重新导出最终 `.glb`。程序生成几何可以在开发阶段执行，但不得在玩家进场时重新生成。原GLB已经完整时可保留原导出，说明无须回写的依据；不能为了有新时间戳空导出。
3. 引擎专用shader、材质和必要场景保存为明确的正式资源；不强求把Godot专用效果塞回GLB，也不把游动、开合嘴、转眼、水下光照烘成固定外观。静态嘴眼几何、UV和权重不能只存在于进场补丁或只序列化在一个临时引擎场景里。
4. **固化在冻结最终验收候选之前。** 保存/重新导入后，检查实际资源、surface、纹理、骨骼、权重、LOD与导入数组；再冻结最终GLB、源blend、实际入口及全部依赖。最终完整门针对这个导出版本运行，不能验证实验版后只做一次未经检查的最终导出。
5. 用新进程直接加载最终入口，关闭/隔离实验静态构建链，记录实际入口、依赖哈希、静态构建调用数和错误日志。不可先加载实验材质/纹理再测冷读，也不可回退到旧builder补齐缺件。检查正常/近景与多视、原生循环、四动作及切换；最终导出与已审阅实验效果并排，实际看图。
6. 执行当前鳍根/全鳍面、身体/GPU、材质锚定与动作/LOD等适用最终门，以及 `volume sop-check`。导出改变了输入时旧报告失效；不批量改哈希、降低容差或以静态截图代替动态验证。
7. 在既有handoff记录最终源文件、GLB、入口、材质/贴图依赖、重放命令、检查与剩余限制。完成后交付实际导出文件及游戏入口，再按引用保留必要证据并清理未采用候选。不能只交一句“已导出”。

### 把运行时静态部件并入模型时

以当前**实际装配后的**身体、鳍、眼等网格为输入，连同 UV、骨骼权重和原骨架/动画一起导出；重新导入后，顶点顺序可能变化，须按位置、UV、权重和有向三角面核对，而不能仅比数组哈希。Godot 专用材质可以保留为引擎资源；把共享贴图明确保存为可重读资源后，重新打开每份材质并验证实际绑定的纹理像素、尺寸和透明设置。保存成功返回码不能代替重新加载检查，尤其注意 ShaderMaterial 内部贴图引用在二进制资源中丢失的情况。

网格重导出或换材质后，鳍根选区按新网格的解剖根带重新建立，再测完整根带和**整片鳍膜**。根部接触通过不意味着膜面与身体无穿入；失败时保留候选与实际报告，恢复原游戏入口，修复几何后重跑正式门。Godot 导入 GLB 可能在项目资产目录另存提取的 PNG；即使正式材质随后覆盖了导入材质，缓存场景也可能继续引用该 PNG。将此类实际依赖与 `.import` 设置一并列入最终文件和哈希清单，清理后新进程冷读，不能凭文件未出现在脚本引用中就删除。

技术固化不是用户外观接受；自动流程也不自动批准新外观。局部修复不得借本门擅自重做其他部位。旧鱼没有固化证据时保留待整理，不追造历史通过，不在更新机制时批量覆盖当前游戏资产。

## SOP账本中的必填字段

沿用原 `production-review.json`，不另建任务状态库。`candidate_files` 至少绑定现有五个角色，另加可编辑blend和实际加载入口、参与的脚本/shader/材质/纹理；角色名可自定，`model` 必须指最终GLB。所有路径/SHA按SOP第9节填写。

`stages.runtime.finalization`：

```json
{
  "state": "exported",
  "editable_source_role": "editable_blend",
  "model_role": "model",
  "entry_role": "final_scene",
  "static_parts": {
    "body": {"geometry_uv_weights_role": "model", "observation": "填写实际身体组成与导出检查"},
    "eyes": {"geometry_uv_weights_role": "model", "observation": "填写实际眼部组成与导出检查"},
    "mouth": {"geometry_uv_weights_role": "model", "observation": "填写实际口部组成与导出检查"},
    "fins": {"geometry_uv_weights_role": "model", "observation": "填写实际鳍组成与导出检查"}
  },
  "engine_resource_roles": ["pixel_material", "pixel_shader"],
  "runtime_behaviors": [
    {"resource_role": "motion_controller", "purpose": "animation", "observation": "填写实际保留的实时动作"}
  ]
}
```

`runtime_behaviors.purpose` 仅可为 `animation/behavior/environment/resource_loading`；这只是依赖分工声明，不能把眼嘴生成代码改名为animation绕过。实际检查仍须关闭静态构建链并观察。没有独立引擎资源/行为时数组可以为空；入口也可直接是完整GLB。

`stages.runtime.checks.final_asset_cold_load` 引用实测JSON报告的证据ID，按原规则填写 `kind=report`、报告文件SHA、完整 `bound_inputs` 和观察；报告除顶层 `ok=true` 外，还须具有：

```json
{
  "kind": "fish_final_asset_cold_load",
  "ok": true,
  "species": "实际物种ID",
  "bound_inputs": {"所有candidate角色": "对应当前SHA256"},
  "entry_role": "final_scene",
  "fresh_process": true,
  "static_builders_disabled": true,
  "runtime_static_build_calls": 0,
  "errors": [],
  "checks": {
    "independent_load": true,
    "materials_complete": true,
    "rig_and_motion": true,
    "export_matches_candidate": true
  }
}
```

以上是报告字段示意，**不是可以复制填写的通过证明**。实际捕获工具/操作者在执行后记录测量、日志路径、代表性画面和观察，证据需随报告保留。`exported_vs_experiment_comparison` 另引 `kind=image` 的实际对照图。无静态修补的新鱼同样提供完整导出与冷读证据，不能省略本门。

## 当前自动化能力与限制

`volume sop-init` 自动创建未完成固化声明；`volume sop-check` 强制检查正式资源角色、完整部位声明、文件存在/非空/SHA及报告结构/物种/全量依赖绑定。缺少导出、仍是实验、冷读用旧候选、静态构建调用非零、错误日志状态或只给通用 `ok=true` 都会阻断。

此检查器**不自动把任意Godot修补算法翻译为Blender，也不启动导出/Godot或证明未披露调用不存在**；逐鱼实际回写、导出、关闭builder的冷读与视觉/专项验证由执行者按上述顺序主动完成。报告字段不是对内容真实性的自动证明。

现有 `volume accept` 记录建模/原画风格阶段的操作者接受，是后续动作生产的输入，不能改为要求尚未制作的运行时全套证据而制造循环依赖。它不等于整鱼最终交付；最终交付必须另通过包含本门的 `volume sop-check`，不能只拿旧的accept状态宣称完成。
