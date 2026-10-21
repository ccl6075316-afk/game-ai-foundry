# 103 · 局部源特征试修（实验，未接受）

仅冻结黑鲷中央重复眼纹桥与真鲷已定位的源头顶墨线域，不是自动去黑色工具。未安装正式游戏。

- 黑鲷`parameters.json`：限定Closed_body/surface0、源眼域与窄中央rest-normal域，侧面真眼受保护。只减轻连接，残余眼纹仍在。供体纹理延续为工程推断。
- 真鲷`red-parameters.json`：`red-head-ink-mask.png`与RGBA坐标donor PNG拷到该JSON指定的`res://assets/models/fish/motion/`路径。冻结3473源像素，后期已撤去法线限制，JSON旧fade字段保留为历史参数，不参与当前红色类型的mask。
- 红色方案在最终ALBEDO附近按friendly UV过滤，不覆盖全部复杂投影/透明回退路径，已由104实际采样wrapper替代；禁止直接推广到主工程所有鱼。
- 调用点在现有材质装配后。mode0原色、1试修、2严格白色EMISSION诊断、3红色叠加；保持源图/GLB/几何/口内/鳍不变。只能在对应冻结输入使用，不是鳍身或视觉验收。

代码/配置与实际GPU证据不互相替代。精确使用过的黑鲷代码及对应材质/模型，随Fish的`experiments/blender-fish/review-105/preview-fixtures/black_seabream`归档；真鲷最新候选见同目录red_seabream（104）。103原始试修与否定结果见`local-source-features-103/trial.validation.json`。
