# 造景内嵌贴图及旧水草合并

游戏提交为 `5ec2b633`。10 件水草从现有来源重新构建的 GLB 和发布字节一致。

## 30 件造景内嵌

aquascape-v9/solids 的 20 件与 aquascape-v11/solids 的 10 件改用 Godot glTF 内嵌无损导入。GLB 的网格、材质和内嵌图字节保持。Godot 复核 30 件装载后的纹素和对应 GLB 内原图一致，导入场景无外置贴图依赖。迁移前提取的 PNG 有 mipmap，内嵌后不生成 mipmap。原材质与覆藻均使用无 mipmap 的最近邻采样。近景、远景、斜后以及适用覆藻的 105 张固定机位截图逐像素一致。删除 30 张自动提取 PNG 和 30 个 .import，共 95.23 MiB。 [Godot 导入模式](https://docs.godotengine.org/en/4.7/classes/class_gltfstate.html#enumerations) · [清理记录](cleanup.validation.json)

## 10 件旧水草合并与顶点水流

旧 V10 的正式布景目录原先加载骨骼版，平行的 shader 水草缸使用非骨骼版本。当前正式布景目录使用已合并的非骨骼版，并由正式摆放入口绑定 RootedCurrent 顶点着色器。使用旧 V10 的逐叶根位、根到尖端权重和叶片相位，原 shader 预览权重与导出字节已核对。正式摆放幅度沿用旧水草缸默认 0.18。保留目录 ID、游戏尺寸、顶点位置、法线、7,208 个三角面和实际使用的原画像素。每件使用一个网格、一个表面、一个材质和一张内嵌图集。旧 GLB 留作来源和已有入口引用。 [合并脚本](../../scripts/aquascape/merge_plant_meshes.py) · [逐件合并报告](merge.validation.json) · [预算](budget.validation.json)

10 件均已实机确认 0 骨骼、0 动作轨，叶片可见实时摆动。81 个计算采样中根部固定，10 秒周期首尾闭合。停用效果后连续截图逐像素一致，恢复后 10 件都出现实际叶片位移。静止与旧版对照每张最多 139 像素变化，最大 RGB 平均误差 0.0118/255。仅放 60 丛水草的同机位 Compatibility 测试中，每帧可见绘制调用由 1,098 次降到 60 次。测试不含鱼、水体或阴影。 [逐件动静图验证](vertex-motion.validation.json) · [绘制调用](draw-calls.validation.json)

当前 102 件按每件单网格、单表面、单材质摆放。全部通过实际摆放、接地与临时存档变换回读。32 个覆藻选项通过材质和存档回读。 [导入验证](native.validation.json) · [摆放报告](placement.validation.json) · [覆藻报告](algae.validation.json)

按用户要求清理本批对照图、重复日志和临时核验目录。保留正式资源、可重建脚本和数值报告。
